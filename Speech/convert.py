import subprocess as sp, os, traceback

# path to ffmpeg bin
FFMPEG_PATH = os.environ['FFMPEG_PATH'] if 'FFMPEG_PATH' in os.environ else '/usr/local/bin/ffmpeg'

def convert(file_path):
    try:
        command = [
            FFMPEG_PATH, '-i', file_path, '-y', '-loglevel', '16','-threads', '8',  '-c:v', 'mp4' , '-f', 'wav' , '-'
        ]
        # Get raw audio from stdout of ffmpeg shell command
        pipe = sp.Popen(command, stdout=sp.PIPE, bufsize=10**8)
        raw_audio = pipe.stdout.read()
        return raw_audio
        
    except Exception, e:
        print Exception
        print e
        traceback.print_exc()