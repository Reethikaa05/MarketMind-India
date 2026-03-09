/**
 * Zero-dependency SSE-to-Stdio Bridge for MCP
 * Works with Node.js 18+ (verified on Node 22)
 */
const https = require('https');
const http = require('http');

async function main() {
    const sseUrl = "https://marketmind-india-13.onrender.com/sse";
    let messageUrl = null;

    const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    };

    // 1. Establish SSE Connection
    const req = https.get(sseUrl, { headers }, (res) => {
        if (res.statusCode !== 200) {
            console.error(`Failed to connect: ${res.statusCode} (Host: ${res.headers.host || 'unknown'})`);
            // Render sometimes returns 421 if it's "cold". We should warn the user.
            if (res.statusCode === 421) {
                console.error("Cloud server is misdirected. Wait 30 seconds and try again.");
            }
            process.exit(1);
        }

        res.on('data', (chunk) => {
            const data = chunk.toString();
            // Process chunks line by line
            const lines = data.split('\n');
            for (const line of lines) {
                if (line.startsWith('data:')) {
                    const content = line.substring(5).trim();
                    if (content.startsWith('/')) {
                        messageUrl = new URL(content, sseUrl).toString();
                    } else if (content.startsWith('{')) {
                        process.stdout.write(content + "\n");
                    }
                }
            }
        });

        res.on('error', (err) => {
            console.error("SSE Connection Error:", err.message);
            process.exit(1);
        });
    });

    req.on('error', (err) => {
        console.error("Request Error:", err.message);
        process.exit(1);
    });

    // 2. Forward Stdin from Claude to the Server via POST
    process.stdin.on('data', async (chunk) => {
        if (!messageUrl) return;

        const msgString = chunk.toString();
        const postReq = https.request(messageUrl, {
            method: 'POST',
            headers: {
                ...headers,
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(msgString),
                'Accept': 'application/json'
            }
        });

        postReq.on('error', (err) => {
            console.error("POST Error:", err.message);
        });

        postReq.write(msgString);
        postReq.end();
    });
}

main().catch(err => {
    console.error("Bridge Fatal Error:", err);
    process.exit(1);
});
