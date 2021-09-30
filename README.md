# Maubot webhooks: receive messages in your matrix chat through HTTP(S)

This is a [maubot](https://github.com/maubot/maubot) plugin to dynamically expose and process webhooks.

## Requirements
To use this, you need the [normal maubot dependencies](https://docs.mau.fi/maubot/). That usually means Python 3 with
the maubot package. This guide does not tell you how to run Maubot, please refer to the official docs for that.

## Installation
1. Build the maubot from source using the official [instructions](https://docs.mau.fi/maubot/usage/cli/build.html):
```bash
$ mbc build
```
2. Upload the .mbp file to your maubot instance (click the + next to "Plugins")
3. Create a maubot client if you haven't already ([docs](https://docs.mau.fi/maubot/usage/basic.html))
4. Click the + next to "Instances" to create a new instance
5. Fill out the form to your liking and hit Create
6. Configure the newly created instance

## Configuration
Configuration is done through the accompanying YAML file. An example is provided in this repository.

### Example YAML
The following example YAML provides two endpoints, a POST endpoint and a GET endpoint.
```yaml
endpoints:
  endpointname:
    notice: false
    room_id: '!......@.....'
    format: JSON
    template: 'Test data: ${user.name} is ${user.mood}'
    methods:
      - POST
  anotherendpoint:
    notice: true
    room_id: '!......@.....'
    template: 'Test data: ${fromQuery}'
    methods:
      - GET
tokens:
 - authtoken1
 - authtoken2
```

All webhooks are protected by tokens by default. All tokens work on all webhooks, though this may be reworked in the future.
A call without a token will be ignored and logged.

Endpoint `endpointname` can only be called through POST requests, accepts JSON as input (the only supported input type
for POST requests at the moment) and sends notifications as normal text messages (those will generate a notification
sound by default!). You can find the room ID that the bot sends to in your favourite Matrix client. This bot does not try
to autojoin rooms, so you'll have to invite maubot to your room for this to work.

You can call this webhook with the following data:
```json
{
  "user": {
    "name": "Willem",
    "mood": "happy"
  }
}
```

The endpoint will be available at a URL relative to your maubot instance. For example, if you run maubot at
https://matrix.example.org/_matrix/maubot/# and you call your maubot instance "webhookbot", the callback URL will be
https://matrix.example.org/_matrix/maubot/plugin/webhookbot/post/endpointname?token=authtoken1

The second endpoint, `anotherendpoint`, accepts data through a GET request. As there is no good way to encode JSON in a
GET request, GET endpoints take data from the query string instead. The second endpoint sends messages as notices (usually
means that no notifications will be sent). The callback URL for this endpoint will be https://matrix.example.org/_matrix/maubot/plugin/webhookbot/post/anotherendpoint?token=authtoken1&fromQuery=itworks123

The above call will send the message `Test data: itworks123` to the defined Matrix room.

## Formatting
Templates can be formatted through markdown, though the allow_html parameter has also been enabled in the code. Because
YAML allows for newlines and such, the following is a valid endpoint definition:

```yaml
endpoints:
  fancy:
    notice: false
    room_id: '!......@.....'
    format: JSON
    template: |
            **Hello, world!**
            
            Check these _sick___markdown__ features!
            <b>HTML works too!</b>
            
            Remember to use double newlines for a paragraph break!
    methods:
      - POST
      - GET
```

### Troubleshooting
Errors will be logged to the maubot log. Info logs are used to indicate startup and to track calls to the endpoints.

If something goes wrong and no error message is logged to the maubot log, check the docker/maubot server output!