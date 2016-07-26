import convert, os

if 'FB_BOT_STT_API_PROVIDER' in os.environ and os.environ['FB_BOT_STT_API_PROVIDER'] == 'GOOGLE':
	from speech_py import speech_to_text_google as STT
else:
	from speech_py import speech_to_text_ibm_rest as STT

def transcribe(audio_url):
	raw_audio = convert.convert(audio_url)
	
	return STT(raw_audio)