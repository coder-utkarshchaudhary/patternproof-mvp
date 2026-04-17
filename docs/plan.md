# Project idea
An auditing service where a user enter's a website url and the system outputs a detailed, comprehensive, accurate and clear report describing all the dark patterns on the website.

## Services
The product caters to 2 types of dark patterns:
1. Static dark patterns -> These occur on a single webpage. Isolated dark patterns that can be detected using conventional models like YOLO or ResNets or other CV models trained on static dark pattern datasets.

2. Dynamic dark patterns -> These occur across webpages in a website and require memory and context from interactions from previous webpages. A stateful agentic approach is required to solve this.

# Technical Aspects
## Solution Architecture
A manager-employee based agentic system where the maneger acts as an orchestrator that performs task delegation to a team of employee agents. Some of the employee agents are:
1. Static DP finder -> Runs the models on the particular webpage UI images, code, text in background. A standalone agent that reports to the manager agent.
2. Dynamic DP finder -> This is a subteam of agents under the manager responsible for detecting dynamic dark patterns.