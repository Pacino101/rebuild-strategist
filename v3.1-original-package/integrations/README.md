# Integration contracts — not connected integrations

This folder defines intended roles only. The package does not include credentials and has not connected to any live service.

Before each connector is implemented, document:
- exact product/version and official API/MCP capability;
- authentication method and scopes;
- data types and fields accessed;
- read/write capabilities;
- rate limits and failure modes;
- test environment and sample result;
- approval/rollback requirements;
- owner and last verification date.

Never paste API secrets into Skill files, agent prompts, logs or version control. Use the platform's secret manager/environment variables if supported.
