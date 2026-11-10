# Live quiz WebSocket

The backend provides one authenticated room endpoint:

```text
ws://127.0.0.1:8000/ws/quizzes/{ROOM_CODE}
wss://localhost/ws/quizzes/{ROOM_CODE}
```

## Using the frontend

1. The host creates a quiz and selects **Open live room as host** beside its
   room code.
2. Each participant enters that code in the Play Quiz tab and selects **Join
   Room**. The frontend first creates the required REST quiz attempt, then
   opens the authenticated WebSocket connection.
3. The host starts each round. Participants select and submit an answer before
   the countdown ends. The answer and standings are revealed only after the
   server sends `ROUND_END`.

The REST **Start Quiz Now** button remains the self-paced practice flow. The
live room client uses the WebSocket events below. For local live rooms, keep one
FastAPI worker running as described in Development limitation.

Use the `wss://` address through the existing local Caddy proxy for encrypted
connections. First, the participant joins the quiz through the REST API so an
active quiz attempt exists. The host uses the account that created the quiz.
The browser should send the access token in WebSocket subprotocols, not in the
URL. The server selects only `csmqp.v1` as the accepted subprotocol:

```javascript
const socket = new WebSocket(
  "wss://localhost/ws/quizzes/ABC123",
  ["csmqp.v1", `bearer.${accessToken}`],
);
```

## Event flow

Messages are JSON objects with a `type` field.

1. When connected, the client receives `ROOM_JOINED` with its `host` or
   `participant` role.
2. The host sends `{"type":"START_QUIZ"}`.
3. Everyone receives `QUESTION_OPEN` with the question, options, round number,
   and a 30-second server deadline. It contains no correct answer or explanation.
4. Each participant sends an answer, for example:

   ```json
   {"type":"SUBMIT_ANSWER","question_id":12,"answer_index":2}
   ```

5. Everyone receives `ANSWER_STATE` with the number of submitted answers. It
   does not include answer choices or participant identities.
6. The server sends `ROUND_END` when every participant connected at round start
   has answered, or when 30 seconds expire. Only this event includes the correct
   answer, explanation, and standings. The host sends `START_QUIZ` again to
   open the next question. The last question completes the quiz attempts.

Invalid messages receive a generic `ERROR` event. The server checks the access
token, quiz host or active attempt, and configured frontend Origin. An invalid
token, unknown room, or unauthorized account is disconnected without returning
credential details.

## Development limitation

Live room membership and timers are held in this backend process's memory. Run
one FastAPI worker for local development. Restarting the backend clears active
room state; this small implementation does not add Redis or distributed room
coordination.
