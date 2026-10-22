terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.67.0"
    }
  }

  # Bucket podawany przy `terraform init -backend-config=...` (zob. README), żeby numer
  # konta nie trafiał do publicznego repo.
  backend "s3" {
    key          = "kupto/terraform.tfstate"
    region       = "eu-north-1"
    profile      = "kupto"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  profile = var.aws_profile
  region  = var.aws_region

  default_tags {
    tags = {
      Project   = "kupto"
      ManagedBy = "terraform"
    }
  }
}
