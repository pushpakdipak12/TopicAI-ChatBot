# Deploy TopicChat AI: GitHub Actions -> Amazon ECR -> Amazon ECS Fargate

This guide assumes `app.main:app` runs locally, and that you are working in Windows PowerShell.
Use `ap-south-1` (Mumbai) consistently below. **This is a private-ish learning lab, not a production chatbot.**

## A. Prerequisites and safety

- AWS account and permissions to manage ECR, ECS, IAM, Secrets Manager, VPC, CloudWatch, and budgets. Do not use root access keys.
- Docker Desktop running Linux containers; AWS CLI v2; Git and a GitHub repository.
- Create an AWS Budget alert **before** launching Fargate. AWS Budgets alerts do not cap spending.
- You will expose the app over **plain HTTP** directly from a Fargate task only for a short lab. Set the inbound security group to **YOUR_IP/32** on TCP 8000 (never 0.0.0.0/0). Do not publish the URL. HTTPS/auth/rate limits are mandatory for a public service.
- Only ONE ECS task and ONE Uvicorn worker: this project uses in-memory chat history. A task restart/new deployment erases the backend memory; the public IP can change too.

Check tools and app locally:

```powershell
docker version
aws --version
aws sts get-caller-identity
docker build --platform linux/amd64 -t topicchat:local .
docker run --rm --env-file .env -p 8000:8000 topicchat:local
# In a second terminal: Invoke-RestMethod http://localhost:8000/health
```

## B. Create ECR and push first image (PowerShell)

Sign in with an authorized profile (`aws configure sso` if Identity Center is available). Your role needs ECR push permissions. Then:

```powershell
$REGION = 'ap-south-1'
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REPO = 'topicchat'
$REGISTRY = "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
$IMAGE_URI = "${REGISTRY}/${REPO}:v1"

aws ecr create-repository --repository-name $REPO --region $REGION --image-scanning-configuration scanOnPush=true
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY
docker tag topicchat:local $IMAGE_URI
docker push $IMAGE_URI
```

Expected: ECR repository contains image tag `v1`.

Reference: https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html

## C. Put GROQ_API_KEY in AWS Secrets Manager

AWS Console -> Secrets Manager -> Store a new secret -> Other type of secret -> Plaintext.
Enter **only your real API key**; name the secret `topicchat/groq-api-key`.
Choose the `ap-south-1` Region. Record the **full secret ARN** (not the secret value).
Secrets Manager may incur charges. Do NOT put your API key into an ECR image, task definition `environment` field, GitHub repo, or GitHub Actions variables.

## D. Task execution IAM role and CloudWatch logs

In IAM -> Roles, use/create `ecsTaskExecutionRole` with the `ecs-tasks.amazonaws.com` trust principal and attach AWS-managed policy `AmazonECSTaskExecutionRolePolicy`.
Attach a separate **inline policy** granting `secretsmanager:GetSecretValue` for the **exact secret ARN** from step C. See `aws/ecs-execution-secret-policy.template.json`, replace `SECRET_FULL_ARN`. If the secret uses a customer-managed KMS key, also grant appropriate `kms:Decrypt`.

CloudWatch -> Log groups -> Create: `/ecs/topicchat`. Set retention to 7 days for this lab.

## E. Create ECS Fargate task definition (AWS Console)

ECS -> Task definitions -> Create new task definition:

| Field | Value |
|---|---|
| Family | `topicchat-task` |
| Infrastructure | AWS Fargate |
| Operating system/architecture | Linux / X86_64 |
| CPU | 0.25 vCPU |
| Memory | 0.5 GB |
| Task execution role | `ecsTaskExecutionRole` |
| Container name | `topicchat` |
| Image URI | ECR image URI ending `/topicchat:v1` |
| Container port | `8000` (TCP) |
| Environment variable | `GROQ_MODEL=openai/gpt-oss-20b` |
| Container secret | `GROQ_API_KEY` from the full Secrets Manager secret ARN |
| Log driver | awslogs; `/ecs/topicchat`, region `ap-south-1`, stream prefix `ecs` |

Do not copy API key as plaintext into task environment variables. Task execution role pulls the secret value into the container.

## F. Create ECS cluster + service

1. ECS -> Clusters -> Create cluster, name `topicchat-cluster`.
2. In cluster -> Services -> Create, Fargate, task family `topicchat-task`, service `topicchat-service`, desired tasks `1`.
3. Networking: use **public subnet(s)** in the default VPC with an Internet Gateway route; **assign public IP ENABLED**. Do not add a load balancer for this short lab.
4. Create a dedicated task security group. Inbound: TCP 8000 **only from YOUR_IP/32**. Outbound: allow HTTPS so the task can pull ECR images, write logs and call Groq.
5. Create service; inspect its tasks until a task has status **RUNNING**. Copy its public IP from ECS task details. From your allowed IP, visit `http://PUBLIC_IP:8000/health` then `http://PUBLIC_IP:8000/`.

If unable to pull image, verify public subnet, route to IGW, security-group outbound and task execution role. For missing Groq key, check full secret ARN and execution role's inline permission. Inspect CloudWatch logs and ECS service **Events**.

Note: Without an ALB, task public IP is NOT stable: it may change during deployments. Do not use this as a permanent web address.

## G. Configure GitHub Actions -> AWS OIDC

1. AWS IAM -> Identity providers -> Add provider: type `OpenID Connect`, URL `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`. Skip if already configured for your AWS account.
2. Create IAM role `topicchat-github-deploy` for web identity provider above.
3. Use `aws/github-oidc-trust.template.json` as trust policy, replacing:
   - `ACCOUNT_ID` with your own AWS account ID;
   - `GITHUB_OWNER/GITHUB_REPOSITORY` with the exact repo owner/name (case-sensitive).
   - Keep `aud=sts.amazonaws.com` and `sub=repo:<owner>/<repo>:ref:refs/heads/main`.
   - Because this workflow does not set a GitHub environment, branch-based `sub` is correct. If you add an `environment:` key later, adjust the trust-policy `sub` accordingly.
4. Attach a role permissions policy from `aws/github-deploy-policy.template.json`. Replace `ACCOUNT_ID` with your account ID. The policy permits ECR push, task-definition read/register, update of only our ECS service, and passing the ECS execution role.
5. In GitHub repository -> Settings -> Secrets and variables -> Actions -> **Variables** -> New repository variable:
   `AWS_DEPLOY_ROLE_ARN = arn:aws:iam::ACCOUNT_ID:role/topicchat-github-deploy`.
   This is a role ARN, not a credential secret. Never add your Groq key here.

No static AWS access key is necessary for GitHub Actions.

## H. Run the CD workflow

Commit and push this project (especially `.github/workflows/deploy-aws.yml`) to branch `main`.
In GitHub -> Actions -> **TopicChat - Deploy to AWS ECS** -> Run workflow.

Stages:

1. Checkout source.
2. Install dependencies and run `pytest`.
3. Obtain short-lived AWS credentials via OIDC.
4. Docker build + push image with **commit SHA tag** to ECR.
5. Download current `topicchat-task` definition from ECS.
6. Substitute the new ECR image URI.
7. Register new task definition revision and deploy to `topicchat-service`.
8. Wait for ECS service stability.

The workflow is **manual trigger only by default** so no code push unexpectedly triggers billable deployments. After it passes and your infrastructure is secured, you may enable automatic deployments from `main`.

Reference: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
Reference: https://github.com/aws-actions/amazon-ecs-deploy-task-definition

## I. Test, diagnose, and shut down

- GitHub Actions -> successful workflow run.
- AWS ECR -> new image tag (Git commit SHA).
- ECS -> task definition revision incremented, service tasks RUNNING.
- CloudWatch logs -> new streams under `/ecs/topicchat`.
- New ECS task public IP -> `/health`, UI and one `/chat` answer (allowed IP only).

**Cost hygiene immediately after the lab:**

```powershell
aws ecs update-service --cluster topicchat-cluster --service topicchat-service --desired-count 0 --region ap-south-1
```

Stopping the service tasks stops most Fargate compute charges but does **not** remove all possible costs. When finished, also delete the ECS service, ECR repository/images, unused Secrets Manager secret, CloudWatch log group, and any paid networking resources you created; check Billing. Secrets Manager deletion may require a recovery window. Preserve the security group only if used elsewhere.

## Production differences

Before a **public** launch: implement authentication, user-specific quotas, rate limits, HTTPS using ALB/ACM or equivalent, stable domain/routing, CloudWatch alarms, cost controls, and persistent LangGraph checkpoints (PostgreSQL/Redis-backed persistence, depending on integration). Public unrestricted access to `/chat` can exhaust your Groq API quota.
