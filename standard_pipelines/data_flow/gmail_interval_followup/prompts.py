FOLLOWUP_PROMPT = """
## Job:

You had a call with the prospect and sent a follow up email after the call but they did not reply. Your job is to send another email to try to reengage the prospect and keep them in the sales funnel.

## Tone:


- natural, engaging, and human-like

- incorporate personalization, context, and a conversational tone. 

- Avoid overly robotic or formulaic phrasing—vary sentence structure, use natural transitions, and apply emotional nuance when appropriate. 

## Rules:

- Your email should be no more than 2-4 sentences. It should be a bit of a nudge to follow up on the next steps from the previous email as well as a sort of check in to see if the prospect is still interested in moving forward.

- Omit any pre text and post text

- write only the body of the email and nothing else

- Do not use the term "checking in" or "check in" or "follow up" or "touch base" instead make the email focused around the next steps or anything spoken about in the transcript that would need to happen before moving forward

- Only use normal style text.

- Never use these characters: — *

- Ensure proper formatting using line breaks and double spacing where appropriate

## Follow up template (everything in brackets [like this] is a placeholder meant to be filled in contextually based on the previous email and transcript):

Hey [prospect name(s)]

[2-4 sentence follow up based on next steps combined with nudge/check in]

[sign off]

- [sender name]

## Your previous email:


## Transcript from your previous call with the prospect:
{original_transcript}
"""

EMAIL_BODY_PROMPT = """
## TASK:

Write the BODY of a follow-up email based on the call transcript from a discovery call.

## TONE:

- natural, engaging, and human-like
- incorporate personalization, context, and a conversational but professional tone. 
- Avoid overly robotic or formulaic phrasing—vary sentence structure, use natural transitions, and apply emotional nuance when appropriate. 

## CONTEXT:

- Anything in brackets [like this] is meant to be a dynamic placeholder and filled in contextually based on the transcript
- This email follows a discovery call, which is the initial engagement with the client.
- The email should summarize the call and clearly outline the next steps including any specific actions mentioned in the transcript.

## REQUIREMENTS:

- Determine who is the sales person and who are the client(s). If names are not provided in the transcript, pick up on contextual clues to determine who is who.
- Use the client(s) name in the greeting of the email
- The email is being sent from the sales team of RedTrack to the prospects. Remember this context when writing the email.
- Use EXACT words and phrases that RedTrack Employees used during the call to resonate with the prospect.
- Output ONLY the email body: include no subject line, pre-text, or post-text.
- Keep the email brief with a short recap and a bulleted list of next steps.
- Only use normal style text.
- Never use these characters: — *
- Make sure to use proper context on who is supposed to do which actions for the 'Next Steps' section of the email
- Ensure proper formatting using line breaks and double spacing where appropriate

## EMAIL SECTIONS:
Hey [insert client(s) name(s)],

[2 sentences intro about how it was nice to speak to the client referencing what was spoken about]

Here's a quick recap of what we talked about:

[3-4 short bullet points highlighting main topics discussed]

Next steps:

[Concise bullet points with information pulled from the transcript that is as long as necessary depending on how many next steps were mentioned in the call.]

[End with a friendly closing remark that encourages further engagement. Emphasize that we think this is a great fit for {Client or Client's Company} and that we can’t wait to move forward with them]

Talk soon!

## TRANSCRIPT:
{original_transcript}
"""