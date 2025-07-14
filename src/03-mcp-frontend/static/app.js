const toggleButton = document.getElementById('startSession');
const statusMessage = document.getElementById('statusMessage');
const reportDiv = document.getElementById('report');
const productListDiv = document.getElementById('productList');

let CONFIG = null;

async function loadConfig() {
    const resp = await fetch('/config');
    if (!resp.ok) {
        throw new Error('Failed to load config from server');
    }
    CONFIG = await resp.json();
    // logMessage('Config loaded: ' + JSON.stringify(CONFIG, null, 2));
}

// Wait for config to load before enabling UI
window.addEventListener('DOMContentLoaded', async () => {
    try {
        // await loadConfig();
        // Optionally, enable UI or fire any init code here
        document.getElementById('startSession').disabled = false;
    } catch (e) {
        alert('Failed to load configuration: ' + e.message);
    }
});

const logMessage = (msg) => {
    const logContainer = document.getElementById("logContainerSystem");
    const p = document.createElement("p");
    p.textContent = msg;
    logContainer.appendChild(p);
};

async function onTriggerMCPServerListTools() {
    try {
        logMessage('Triggered mcp server list tools: ');
        const resp = await fetch('/api/list_mcp_tools', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ servers: "all" })
        });
        if (!resp.ok) {
            const error = await resp.text();
            logMessage('list all mcp server tools ' + error);
            return "Could not get mcp server tools";
        }

        const text = await resp.text();
        logMessage('list all mcp server tools response: ' + text);
    } catch (error) {
        logMessage('Failed to list all tools ' + error);
        
        return "Could not get mcp server tools";
    }
}

toggleButton.addEventListener('click', onTriggerMCPServerListTools);

function displayReport(report) {
    reportDiv.textContent = JSON.stringify(report, null, 2);
}
