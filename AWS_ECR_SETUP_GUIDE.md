# AWS ECR & OIDC GitHub Actions Setup Guide

To get the GitHub Actions pipeline (`.github/workflows/ecr-push.yml`) successfully pushing to ECR without long-lived access keys, you need to configure 3 things in your AWS Account (`444842679762` in `eu-north-1`):

## 1. Create the ECR Repository
As you mentioned, you need to create the container registry:
1. Open the Amazon ECR console.
2. Ensure you are in the `eu-north-1` region.
3. Click "Create repository".
4. Set visibility to **Private**.
5. Set Repository name to: **`ai-designer-repo`**
6. Leave other defaults and hit "Create".

## 2. Create the GitHub OIDC Identity Provider (If not already done)
To allow GitHub Actions to securely request temporary AWS keys, AWS needs to trust GitHub.
1. Open the IAM console -> **Identity providers**.
2. Click **Add provider**.
3. Select **OpenID Connect**.
4. **Provider URL**: `https://token.actions.githubusercontent.com`
   - *Click "Get thumbprint"* to verify the certificate.
5. **Audience**: `sts.amazonaws.com`
6. Click **Add provider**.

## 3. Create the IAM Role (`GithubActionsECRPushRole`)
This role dictates *what* GitHub Actions can do once authenticated.
1. Go to IAM console -> **Roles** -> **Create role**.
2. **Trusted entity type**: Select **Web identity**.
3. **Identity provider**: Select the GitHub OIDC you just made (`token.actions.githubusercontent.com`).
4. **Audience**: `sts.amazonaws.com`.
5. Under "GitHub organization", put your username (`akshaychovva` or whatever your GitHub org is).
   - *Optional:* You can restrict the "GitHub repository" strictly to your frontend repo name (e.g. `ai_designer_app`).
6. Click **Next**.

### Add Permissions
The role needs power to authorize and push strictly to ECR.
Click "Create policy", use this JSON, name it `ECR-Push-Policy`, and attach it to the role:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "arn:aws:ecr:eu-north-1:444842679762:repository/ai-designer-repo"
        }
    ]
}
```
7. Click Next, name the role **exactly**: `GithubActionsECRPushRole`.
8. Create it!

### Done!
Once you push your code to GitHub, the pipeline will detect changes on `master`, safely assume that IAM Role, build your singular Streamlit container, and deploy it straight to your new ECR repo.
