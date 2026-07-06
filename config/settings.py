import os


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_bool(name: str, default: bool) -> bool:
    default_str = "true" if default else "false"
    return _env(name, default_str).lower() in ("1", "true", "yes")


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
        "DevOps", "SRE", "Site Reliability", "Cloud", "Platform", "DevSecOps",
        "Infra", "Infrastructure",
    ]

    min_skill_match = 10
    max_applications_per_run = 15

    def __init__(self):
        self.linkedin_email = _env("LINKEDIN_EMAIL")
        self.linkedin_password = _env("LINKEDIN_PASSWORD")

        self.naukri_email = _env("NAUKRI_EMAIL")
        self.naukri_password = _env("NAUKRI_PASSWORD")

        self.smtp_host = _env("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(_env("SMTP_PORT", "465"))
        self.smtp_use_ssl = _env_bool("SMTP_USE_SSL", True)
        self.smtp_user = _env("SMTP_USER", _env("GMAIL_USER"))
        self.smtp_password = _env("SMTP_PASSWORD", _env("GMAIL_APP_PASSWORD"))
        self.smtp_from = _env("SMTP_FROM", self.smtp_user)
        self.alert_email = _env("ALERT_EMAIL")

        self.twilio_account_sid = _env("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = _env("TWILIO_AUTH_TOKEN")
        self.twilio_whatsapp_from = _env("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        self.whatsapp_to = _env("WHATSAPP_TO")

        # Notification feature flags
        self.enable_email_alerts = _env_bool("ENABLE_EMAIL_ALERTS", False)
        self.enable_whatsapp_alerts = _env_bool("ENABLE_WHATSAPP_ALERTS", True)

        self.db_path = "data/applied_jobs.db"
        self.headless = True