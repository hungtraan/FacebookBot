# Retrieve file from Facebook

import urllib, convert, re, os
# from speech_py import speech_to_text_google as STT
from speech_py import speech_to_text_ibm_rest as STT

def transcribe(audio_url):
	if not os.path.isdir('./audio/retrieved_audio'):
		os.makedirs('./audio/retrieved_audio')
		print "Created dir %s/audio/retrieved_audio"%(os.getcwd())
		print os.path.isdir('./audio/retrieved_audio')
	print os.getcwd()
	reg_ex = '\w+.mp4'
	file_name = re.search(reg_ex, audio_url).group(0)
	urllib.urlretrieve(audio_url, './audio/retrieved_audio/{}'.format(file_name))
	convert.convert('./audio/retrieved_audio/{}'.format(file_name))
	# Converted in: ./converted/{name}.wav
	return STT('./audio/converted/{}'.format(file_name[:-4]+".wav"))
