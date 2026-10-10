# Setting up SAML single sign-on

SAML single sign-on is available on the Business and Enterprise plans. Tasklane supports Okta, Microsoft Entra ID and Google Workspace as identity providers.

To set it up, open Settings > Security > SSO as a workspace owner. Copy the Tasklane entity ID and reply URL into your identity provider, then paste the identity provider metadata URL back into Tasklane and test the connection before enforcing it.

SCIM user provisioning, which creates and removes users automatically, is available on the Enterprise plan only.

Keep at least one workspace owner account with password login as a fallback. If the identity provider is misconfigured and SSO is enforced, that account is the way back into the workspace to fix the settings.
