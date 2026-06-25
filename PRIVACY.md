// NOTICE: This file is protected under RCF-PL
# Privacy Policy for AladdinAI GitHub Bot

**Last Updated:** May 30, 2026

## Overview

AladdinAI GitHub Bot ("the Bot") is an open-source GitHub App that provides automated responses to repository events. This Privacy Policy explains how the Bot handles data when installed in your GitHub repositories.

## Data Controller

**AladdinAI Project**  
Maintained by: Aladdin Aliyev  
Contact: aladdin@aliyev.site  
Repository: https://github.com/aliyevaladddin/AladdinAI

## What Data We Collect

The Bot receives webhook payloads from GitHub containing:

- **Repository Information:** Repository name, owner, URL
- **Event Metadata:** Pull request numbers, issue numbers, commit SHAs
- **User Information:** GitHub usernames, display names (as provided by GitHub)
- **Content:** PR titles, issue titles, comment text (only when @mentioned)

**We do NOT collect:**
- Email addresses
- IP addresses (beyond what Cloudflare logs for 24 hours)
- Repository code or file contents
- Personal information beyond GitHub usernames
- Analytics or usage tracking data

## How We Use Data

Data received via webhooks is used exclusively to:

1. Generate automated welcome messages for pull requests
2. Acknowledge new issues
3. Respond to @AladdinAI mentions in comments
4. Celebrate merged PRs and closed issues

**Processing is entirely automated.** No human reviews webhook data unless debugging a reported issue.

## Data Storage and Retention

**Zero Persistent Storage:**
- Webhook payloads are processed in-memory and immediately discarded
- No database or persistent storage exists
- No data is retained after processing

**Temporary Logs:**
- Cloudflare Functions logs are retained for 24 hours for debugging purposes
- Logs contain only error messages and event types (no personal data)
- Logs are automatically purged after 24 hours

## Data Sharing

**We do NOT share data with third parties.**

The Bot uses the following services:
- **Cloudflare Pages:** Hosts the webhook handler (data processed in-memory only)
- **GitHub API:** Receives webhooks and posts comments (data stays within GitHub)

No data is sold, rented, or shared with advertisers, analytics providers, or other third parties.

## Data Security

**Security Measures:**
- All communication over HTTPS/TLS 1.3

- Webhook signature verification (HMAC-SHA256)

- Constant-time signature comparison (timing attack protection)

- Secrets stored in encrypted Cloudflare environment variables
- Open-source codebase (community auditable)

## Your Rights (GDPR)

Under GDPR, you have the right to:

- **Access:** Request what data we process (Answer: None stored)
- **Rectification:** Correct inaccurate data (N/A - no storage)
- **Erasure:** Request data deletion (N/A - no storage)
- **Portability:** Export your data (N/A - no storage)
- **Object:** Object to processing (Uninstall the GitHub App)

**To exercise rights:** Uninstall the AladdinAI GitHub App from your repository settings.

## Children's Privacy

The Bot does not knowingly collect data from individuals under 13 years of age. GitHub's Terms of Service require users to be at least 13 years old.

## International Data Transfers

Webhook processing occurs on Cloudflare's global edge network. Data is processed in the nearest edge location to your GitHub repository (typically US or EU). No data is stored or transferred beyond processing.

## Changes to This Policy

We may update this Privacy Policy from time to time. Changes will be posted at:
https://github.com/aliyevaladddin/AladdinAI/blob/main/PRIVACY.md

Continued use of the Bot after changes constitutes acceptance of the updated policy.

## Open Source Transparency

The Bot is fully open-source under Apache 2.0 License:
https://github.com/aliyevaladddin/AladdinAI


You can audit the code to verify our data handling practices.

## Contact

For privacy questions or concerns:
- **Email:** aladdin@aliyev.site
- **GitHub Issues:** https://github.com/aliyevaladddin/AladdinAI/issues
- **Security Issues:** Use GitHub Security Advisories

## Compliance

- **GDPR Compliant:** No personal data storage, legitimate interest basis
- **GitHub Marketplace:** Adheres to GitHub Marketplace Developer Agreement
- **Open Source:** Apache 2.0 License, community auditable
