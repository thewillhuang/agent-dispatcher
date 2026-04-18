# Agent Dispatcher - Shell Scripts

## Run Dispatcher Once

```bash
python3 agent-dispatcher.py
```

## Run Dispatcher with Logging

```bash
python3 agent-dispatcher.py >> /var/log/agent-dispatcher.log 2>&1
```

## Install as Systemd Service

```bash
sudo cp systemd-service.service /etc/systemd/system/agent-dispatcher.service
sudo systemctl daemon-reload
sudo systemctl enable --now agent-dispatcher
```

## Check Service Status

```bash
sudo systemctl status agent-dispatcher
sudo journalctl -u agent-dispatcher -f
```

## Manual Testing

```bash
# Test board query
gh api graphql -f 'query=query { repository(owner: "thewillhuang", name: "agentneo") { projectsV2(first: 1) { nodes { items(first: 100) { nodes { id } } } } }'

# Test claim mutation
gh api graphql -f 'mutation={ updateProjectV2ItemFieldValue(input: {projectId: "PVT_kwHOAHgLT84BUsgT", itemId: "1", fieldId: "PVTSSF_lAHOAHgLT84BUsgTzhCINu8", value: {singleSelectOptionId: "47fc9ee4"}}) }'
```