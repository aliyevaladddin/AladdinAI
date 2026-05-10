import { redirect } from "next/navigation";

export default function WebhooksRedirectPage() {
  redirect("/dashboard/automations?tab=webhooks");
}
