# Enterprise playground for agents


## Deploy Basic foundry setup

[Deploy To Azure](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fazure-ai-foundry%2Ffoundry-samples%2Frefs%2Fheads%2Fmain%2Fsamples%2Fmicrosoft%2Finfrastructure-setup%2F40-basic-agent-setup%2Fbasic-setup.json)


## Smoke test

0. Login into azure cli `azure login`

1. Retrieve "Azure AI Foundry project endpoint" from Foundry project overview 

2. Rename .env_template to .env and set foundry project env variable

3. Run `python ./src/00-hello-world/agent.py`