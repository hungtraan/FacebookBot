import urllib, convert, os

if 'FB_BOT_STT_API_PROVIDER' in os.environ and os.environ['FB_BOT_STT_API_PROVIDER'] == 'GOOGLE':
	from speech_py import speech_to_text_google as STT
else:
	from speech_py import speech_to_text_ibm_rest as STT

def transcribe(audio_url):
	# Retrieve file from Facebook
	temp_audio = urllib.urlretrieve(audio_url)
	# Convert Facebook audio attachment's mp4 to Speech-to-Text service 
	# readable wav format file
	raw_audio = convert.convert(temp_audio[0])
	
	return STT(raw_audio)