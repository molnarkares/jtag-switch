// Polling-based status updates (no WebSocket)
let systemInfoTimer = null;
let jtagStateTimer = null;  // Separate timer for JTAG state polling
const SYSTEM_INFO_POLL_INTERVAL_MS = 10000;  // Poll system info every 10s
const JTAG_STATE_POLL_INTERVAL_MS = 2000;    // Poll JTAG state every 2s
const FETCH_TIMEOUT_MS = 3000;               // Fetch timeout (3 seconds)

// ============================================================================
// Fetch with Timeout - Detect disconnections quickly
// ============================================================================
async function fetchWithTimeout(url, options = {}, timeout = FETCH_TIMEOUT_MS) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timeout');
        }
        throw error;
    }
}

// ============================================================================
// Initial Load - Fetch all data once when page loads
// ============================================================================
async function loadInitialData() {
    try {
        const response = await fetchWithTimeout('/api/status');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        updateAllUI(data);
        setConnected(true);

    } catch (error) {
        console.error('Failed to load initial data:', error);
        setConnected(false);
    }
}

// ============================================================================
// JTAG Switch Control - Immediate feedback from POST response
// ============================================================================
async function setSelect(line, connector) {
    try {
        const response = await fetchWithTimeout('/api/select', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({line, connector})
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Use response to update UI immediately (no waiting for poll)
        const data = await response.json();

        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }

        // Response contains updated GPIO states - reflect them immediately
        if (data.select0 !== undefined) {
            updateJTAGState('line0-state', data.select0);
        }
        if (data.select1 !== undefined) {
            updateJTAGState('line1-state', data.select1);
        }

        setConnected(true);

    } catch (error) {
        alert('Network error: ' + error.message);
        setConnected(false);
    }
}

async function toggle(line) {
    try {
        const response = await fetchWithTimeout('/api/toggle', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({line})
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }

        // Fetch fresh status after toggle to get updated states
        await loadInitialData();
        setConnected(true);

    } catch (error) {
        alert('Network error: ' + error.message);
        setConnected(false);
    }
}

// ============================================================================
// System Info Polling - Only for network/system stats (infrequent)
// ============================================================================
function startSystemInfoPolling() {
    stopSystemInfoPolling();

    // Start periodic polling of system info
    systemInfoTimer = setInterval(pollSystemInfo, SYSTEM_INFO_POLL_INTERVAL_MS);
}

function stopSystemInfoPolling() {
    if (systemInfoTimer) {
        clearInterval(systemInfoTimer);
        systemInfoTimer = null;
    }
}

async function pollSystemInfo() {
    try {
        const response = await fetchWithTimeout('/api/status');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Only update system/network info (not JTAG switch states from poll)
        updateSystemInfo(data);
        setConnected(true);

    } catch (error) {
        console.error('Failed to poll system info:', error);
        setConnected(false);
    }
}

// ============================================================================
// JTAG State Polling - Check for external changes (e.g., serial console)
// ============================================================================
async function pollJTAGState() {
    try {
        const response = await fetchWithTimeout('/api/status');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Only update JTAG states (not system/network info to avoid redundancy)
        if (data.select0 !== undefined) {
            updateJTAGState('line0-state', data.select0);
        }
        if (data.select1 !== undefined) {
            updateJTAGState('line1-state', data.select1);
        }
        setConnected(true);

    } catch (error) {
        console.error('Failed to poll JTAG state:', error);
        setConnected(false);
    }
}

function startJTAGStatePolling() {
    stopJTAGStatePolling();
    jtagStateTimer = setInterval(pollJTAGState, JTAG_STATE_POLL_INTERVAL_MS);
}

function stopJTAGStatePolling() {
    if (jtagStateTimer) {
        clearInterval(jtagStateTimer);
        jtagStateTimer = null;
    }
}

// ============================================================================
// UI Update Functions
// ============================================================================

// Update all UI elements (used on initial load)
function updateAllUI(data) {
    // Update JTAG switch states
    if (data.select0 !== undefined) {
        updateJTAGState('line0-state', data.select0);
    }
    if (data.select1 !== undefined) {
        updateJTAGState('line1-state', data.select1);
    }

    // Update system/network info
    updateSystemInfo(data);
}

// Update only system/network info (used during polling)
function updateSystemInfo(data) {
    // Network info
    if (data.network) {
        document.getElementById('net-ip').textContent = data.network.ip;
        document.getElementById('net-mac').textContent = data.network.mac;
        document.getElementById('net-mode').textContent =
            data.network.dhcp ? 'DHCP' : 'Static';
        const linkEl = document.getElementById('net-link');
        linkEl.className = 'status-led ' + (data.network.link ? 'on' : 'off');
    }

    // System info
    if (data.system) {
        document.getElementById('sys-uptime').textContent =
            formatUptime(data.system.uptime);
        document.getElementById('sys-ram').textContent =
            formatBytes(data.system.heap_used);
    }
}

// Update JTAG switch state display
function updateJTAGState(elementId, enabled) {
    document.getElementById(elementId).textContent =
        enabled ? 'Enabled' : 'Disabled';
}

// Connection indicator
function setConnected(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.textContent = 'Connected';
        statusEl.className = 'status-indicator connected';
    } else {
        statusEl.textContent = 'Disconnected';
        statusEl.className = 'status-indicator disconnected';
    }
}

// ============================================================================
// Network Configuration Modal
// ============================================================================
function showNetworkConfig() {
    // Refresh system info when opening config
    pollSystemInfo();
    document.getElementById('config-modal').style.display = 'flex';
}

function hideNetworkConfig() {
    document.getElementById('config-modal').style.display = 'none';
}

document.getElementById('network-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const data = {mode};

    if (mode === 'static') {
        data.ip = document.getElementById('ip').value;
        data.netmask = document.getElementById('netmask').value;
        data.gateway = document.getElementById('gateway').value;
    }

    try {
        const response = await fetchWithTimeout('/api/network/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            alert('Configuration saved. Device will restart...');
            hideNetworkConfig();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Network error: ' + error.message);
    }
});

// Toggle static fields visibility
document.querySelectorAll('input[name="mode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        document.getElementById('static-fields').style.display =
            e.target.value === 'static' ? 'block' : 'none';
    });
});

// ============================================================================
// Utility Functions
// ============================================================================
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${mins}m`;
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// Load system info on startup
async function loadSystemInfo() {
    try {
        const response = await fetchWithTimeout('/api/info');
        const data = await response.json();
        document.getElementById('sys-device').textContent = data.device;
        document.getElementById('sys-version').textContent = data.version;
    } catch (error) {
        console.error('Failed to load system info:', error);
    }
}

// ============================================================================
// Initialization
// ============================================================================
window.addEventListener('load', async () => {
    // Load system info (device name, version)
    await loadSystemInfo();

    // Load all status data once on page load
    await loadInitialData();

    // Start polling system info (10s interval)
    startSystemInfoPolling();

    // Start polling JTAG state (2s interval)
    startJTAGStatePolling();
});

// Stop polling when page unloads (cleanup)
window.addEventListener('beforeunload', () => {
    stopSystemInfoPolling();
    stopJTAGStatePolling();
});
