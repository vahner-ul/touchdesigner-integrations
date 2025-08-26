import chalk from 'chalk';
import https from 'https';
import axios from 'axios';
import { WebSocketServer } from 'ws';
import { Telegraf, Markup } from "telegraf";
import fetch from 'node-fetch';
import { message } from 'telegraf/filters';
import certificate from './ssl/certificate.mjs';

const HOST = '<SERVER_HOST>';
const BOT_TOKEN = '<PASTE_YOUR_TOKEN_HERE>';
const WSS_PORT = 4043;

const httpsServer = https.createServer(certificate);

httpsServer.listen(WSS_PORT, () => {
  console.log(`Websocket HTTPS server running wss://digitsu.dev:${WSS_PORT}`);
});

// Create a WebSocket server completely detached from the HTTP server.
const wss = new WebSocketServer({ server: httpsServer });
let wssClients = new Set();

wss.on('connection', (ws) => {
  ws.on('error', console.error);

  wssClients.add(ws);

  console.log(chalk.blue('Info: New WebSocket client connected. Total clients: ' + wssClients.size));

  ws.on('close', () => {
    wssClients.delete(ws);
    console.log(chalk.blue('Info: WebSocket client disconnected. Total clients: ' + wssClients.size));
  });

  ws.send('server: connected to REX lab WS server');
});

// Function to broadcast messages to all WebSocket clients
const broadcastToClients = (message) => {
  for (let ws of wssClients) {
    if (ws.readyState === ws.OPEN) {
      ws.send(message);
    }
  }
}

const rexlab_bot = new Telegraf(BOT_TOKEN, {
  telegram: {
    webhook: {
      domain: HOST,
      hookPath: '/rexlab_bot_api',
      port: 4020,
      tlsOptions: certificate,
    }
  }
});

const defReplies = {
  help: (ctx) => {
    ctx.reply('This bot is designed to send messages to connected TD clients')
  },
  status: (ctx) => {
    if (wssClients.size > 0) {
      ctx.reply(`${wssClients.size} WebSocket clients connected`);
    } else {
      ctx.reply('No WebSocket clients connected');
    }
  }
}

rexlab_bot.start((ctx) => {
  ctx.reply('Welcome to REX lab interactive bot!', Markup.keyboard([
    ['Help'],
    ['Status'],
  ]).oneTime().resize());
})

// Handling text messages (button presses)
rexlab_bot.hears('Help', defReplies.help);
rexlab_bot.hears('Status', defReplies.status);

rexlab_bot.help(defReplies.help);
rexlab_bot.command('status', defReplies.status);

rexlab_bot.on(message('text'), async(ctx) => {
  // Forwarding received message to all WebSocket clients
  const message = ctx.message.text;
  broadcastToClients(message);

  // Responding back to the Telegram user
  const prompt = 'answer using same language as input message, short answer, funny and sarcastic, no questions. input message = ' + message;
  let answer = await askChatGPT(prompt) || 'Thank you for your message'

  ctx.reply(answer);
});

rexlab_bot.on(message('photo'), async(ctx) => {
  // Get file details
  const fileId = ctx.message.photo[ctx.message.photo.length - 1].file_id;
  const fileUrl = await ctx.telegram.getFileLink(fileId);

  // Fetch the image
  const response = await fetch(fileUrl);
  const imageBuffer = await response.buffer();

  // Send to all connected WebSocket clients
  broadcastToClients(imageBuffer);
});

const apiKey = '<PASTE_API_KEY>'; // Replace with your API key
const endpoint = 'https://api.openai.com/v1/chat/completions'; // API endpoint

const askChatGPT = async(promptText) => {
  try {
    const response = await axios.post(
      endpoint, {
        messages: [{ role: "user", content: promptText }],
        model: "gpt-3.5-turbo",
        max_tokens: 50
      }, {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    return response.data.choices[0].message.content.trim();
  } catch (error) {
    console.error('Error calling ChatGPT API:', error);
    return null;
  }
}




export default rexlab_bot;