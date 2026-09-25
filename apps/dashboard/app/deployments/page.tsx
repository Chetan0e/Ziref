import { redirect } from 'next/navigation';

export default function DeploymentsRedirect() {
  redirect('/dashboard/deployments');
}
