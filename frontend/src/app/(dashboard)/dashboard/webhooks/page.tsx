// NOTICE: This file is protected under RCF-PL
import { redirect } from "next/navigation";

export default function WebhooksRedirectPage() {
  redirect("/dashboard/automations?tab=webhooks");
}
