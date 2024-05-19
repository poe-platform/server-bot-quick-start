curl -s -X POST \
  https://api.poe.com/bot/GPT-3.5-Turbo \
  -H 'host: api.poe.com' \
  -H 'content-length: 404' \
  -H 'accept-encoding: gzip, deflate, br' \
  -H 'user-agent: python-httpx/0.24.1' \
  -H 'accept: text/event-stream' \
  -H "authorization: Bearer $POE_API_KEY" \
  -H 'cache-control: no-store' \
  -H 'content-type: application/json' \
  -d '{"version": "1.0", "type": "query", "query": [{"role": "user", "content": "Hello world", "content_type": "text/markdown", "timestamp": 0, "message_id": "", "feedback": [], "attachments": []}], "user_id": "", "conversation_id": "", "message_id": "", "metadata": "", "api_key": "<missing>", "access_key": "<missing>", "temperature": 0.7, "skip_system_prompt": false, "logit_bias": {}, "stop_sequences": []}' \
  | awk -F'"text":' '/"text":/ {print $2}' | tr -d '}' | tr -d '"'