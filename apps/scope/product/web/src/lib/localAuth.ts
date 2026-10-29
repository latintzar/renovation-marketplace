/** Cookie-authenticated local service implementing the existing auth call contract. */
import {appBase} from './runtime';
let pending: Promise<any> | null = null;
async function session() {
  if (!pending) pending = fetch(`${appBase}/api/local/session`, {credentials: 'same-origin'})
    .then(async response => {if (!response.ok) throw new Error('Open your workspace again.');return response.json();})
    .finally(() => {pending = null;});
  return pending;
}
const configured = async () => ({error: {message: 'Connect your account provider.'}});
export const localAuthClient = {
  auth: {
    getSession: async () => {const data = await session();return {data: {session: data.user ? {user: data.user, access_token: ''} : null}, error: null};},
    getUser: async () => ({data: {user: (await session()).user}, error: null}),
    onAuthStateChange: (callback: any) => {let active = true;session().then(data => {if (active) callback('INITIAL_SESSION', {user: data.user, access_token: ''});});return {data: {subscription: {unsubscribe() {active = false;}}}};},
    signOut: async () => {await fetch(`${appBase}/api/local/session`, {method: 'DELETE', credentials: 'same-origin'});return {error: null};},
    updateUser: async (attributes: any) => {const response = await fetch(`${appBase}/api/local/session`, {method: 'PATCH', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({preferred_language: attributes.data?.preferred_language})});return {data: await response.json(), error: response.ok ? null : {message: 'Choose English or Spanish.'}};},
    signInWithOAuth: configured,
    signInWithOtp: configured,
  },
};
