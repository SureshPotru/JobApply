import os


class Settings:
    """All configuration loaded from environment variables."""

    search_keywords = [
        "DevOps Engineer",
        "Site Reliability Engineer",
        "Cloud Engineer",
        "Platform Engineer",
        "DevSecOps Engineer",
    ]
    location = "Hyderabad"
    min_experience = 5

    target_skills = [
        "AWS", "Kubernetes", "Docker", "Terraform", "Git", "GitHub Actions",
        "EKS", "CI/CD", "Jenkins", "Prometheus", "Grafana", "Datadog",
        "Ansible", "Helm", "ArgoCD", "Linux", "Bash", "Python",
        "CloudWatch", "EC2", "S3", "VPC", "IAM",
        "PagerDuty", "ELK", "Elasticsearch", "Nagios", "Zabbix",
    ]

    # Minimum % of target skills that must appear in the job posting
    min_skill_match = 30

    # Max applications per platform per run
    max_applications_per_run = 15

    def __init__(self):
        self.linkedin_email    = os.environ.get("LINKEDIN_EMAIL", "")
        self.linkedin_password = os.environ.get("LINKEDIN_PASSWORD", "")

        self.naukri_email    = os.environ.get("NAUKRI_EMAIL", "")
        self.naukri_password = os.environ.get("NAUKRI_PASSWORD", "")

        self.gmail_user         = os.environ.get("GMAIL_USER", "")
        self.gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
        self.alert_email        = os.environ.get("ALERT_EMAIL", "")

        self.twilio_account_sid   = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token    = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.twilio_whatsapp_from = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        self.whatsapp_to          = os.environ.get("WHATSAPP_TO", "")

        self.db_path  = "data/applied_jobs.db"
        self.headless = True
