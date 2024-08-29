# Catbot

Most users of the Poe protocol will be Large Language Models (LLMs) that perform some
useful task for users. But for this example, we'll instead build a Small Cat Model
(SCM). This example is intended to cover most of the options that the protocol provides,
so you can use it to see the full protocol in action in the Poe app. It doesn't use an
LLM or provide a compelling user experience; we're providing it merely as a sample so
you can build more useful bots. There is a running example of the bot at
[CatBotDemo](https://poe.com/CatBotDemo).

The SCM represents a simple cat with just a few behaviors:

- He likes to eat cardboard. If he receives a message that contains the string
  "cardboard", he responds with "crunch crunch".
- He likes to beg for food. If he receives a message that contains one of the strings
  "kitchen", "meal", or "food", he responds with "meow meow". He suggests the reply
  "Feed the cat".
- The cat doesn't like strangers, and if he sees one he hides and periodically checks if
  it's safe to come out. If a message contains "stranger", he responds "peek" 10 times,
  with a one-second wait in between.
- The cat doesn't like to eat square cat snacks and gets confused when he sees one. If a
  message contains "square", he responds with an error message. If a message contains
  "cube", he gets even more confused and produces an error that does not allow retries.
- The cat is proficient in text rendering technologies. He responds in Markdown by
  default, but if the message contains "plain" he responds in plain text. If the message
  contains "markdown", he gets excited and sends a message demonstrating his knowledge
  of markdown.
- The cat can count. If you send a message that contains "count", he replies with "1",
  waits a second, then replaces his response with "2", and so on until 10. If you add
  "quickly", he doesn't sleep while counting.
- If you call him a dog, he doesn't want to talk to you any more. If the message
  contains "dog", he turns off suggested replies.
- Otherwise, he sleeps. He responds with "zzz".
