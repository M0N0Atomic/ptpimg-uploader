import sys
import requests
import os
import subprocess
import shlex
import contextlib
import mimetypes
from io import BytesIO
from pymediainfo import MediaInfo

argc=len(sys.argv)
if argc==1:
    print("""Usage: ptpimg_uploader.py -k API_KEY .. 
Captures screenshots and uploads images to ptpimg, spitting out mediainfo & urls.""")
    sys.exit()

def getVideoDuration(fname):
    media_info = MediaInfo.parse(fname)
    for track in media_info.tracks:
        if track.track_type == "Video":
            if isinstance(track.duration,int):
                return int(track.duration/1000)
            return int(track.duration.split(".",1)[0])/1000

def getFilename(fname):
    if os.name == 'nt':
        return fname.rsplit("\\",1)[-1]
    return fname.rsplit("/",1)[-1]

def getMediainfo(fname):
    outstr = MediaInfo.parse(fname,full=False,output="")
    return outstr

def getscreenshot():
    screenshot = input("Do you want to take screenshots? [Y/n]:")
    if not screenshot.lower() == 'n':
        fname=input("Enter file path with extension: ")
        no=int(input("Enter no. of screenshots: "))
        vid=getVideoDuration(fname)
        ss=str(int(vid/no))
        command="ffmpeg -i '"+fname+"' -vf fps=1/"+ss+" img%d.png"
        subprocess.call(shlex.split(command))
        screenshots = [x for x in os.listdir() if x.endswith(".png")]
    elif screenshot.lower() == 'n':
        prompt = "Do you want to upload from url? [Y/n]"
        if not prompt.lower() == 'n':
            screenshots = [ x for x in input('Enter urls seperated by space').split()]
    else:
        print("Uploading Existing Images...")
        screenshots = [x for x in os.listdir() if x.endswith(".png")]
    return screenshots

mimetypes.init()

class UploadFailed(Exception):
    def __str__(self):
        msg, *args = self.args
        return msg.format(*args)

class PtpimgUploader:
    """ Upload image or image URL to the ptpimg.me image hosting """

    def __init__(self, api_key, timeout=None):
        self.api_key = api_key
        self.timeout = timeout

    @staticmethod
    def _handle_result(res):
        image_url = 'https://ptpimg.me/{0}.{1}'.format(
            res['code'], res['ext'])
        return image_url

    def _perform(self, files=None, **data):
        # Compose request
        headers = {'referer': 'https://ptpimg.me/index.php'}
        data['api_key'] = self.api_key
        url = 'https://ptpimg.me/upload.php'

        resp = requests.post(
            url, headers=headers, data=data, files=files, timeout=self.timeout)
        # pylint: disable=no-member
        if resp.status_code == 200:
            try:
                # print('Successful response', r.json())
                # r.json() is like this: [{'code': 'ulkm79', 'ext': 'jpg'}]
                return [self._handle_result(r) for r in resp.json()]
            except ValueError as e:
                raise UploadFailed(
                    'Failed decoding body:\n{0}\n{1!r}', e, resp.content
                ) from None
        else:
            raise UploadFailed(
                'Failed. Status {0}:\n{1}', resp.status_code, resp.content)

    def upload_files(self, *filenames):
        """ Upload files using form """
        # The ExitStack closes files for us when the with block exits
        with contextlib.ExitStack() as stack:
            files = {}
            for i, filename in enumerate(filenames):
                open_file = stack.enter_context(open(filename, 'rb'))
                mime_type, _ = mimetypes.guess_type(filename)
                if not mime_type or mime_type.split('/')[0] != 'image':
                    raise ValueError(
                        'Unknown image file type {}'.format(mime_type))

                name = os.path.basename(filename)
                try:
                    # until https://github.com/shazow/urllib3/issues/303 is
                    # resolved, only use the filename if it is Latin-1 safe
                    name.encode('latin1')
                except UnicodeEncodeError:
                    name = 'justfilename'
                files['file-upload[{}]'.format(i)] = (
                    name, open_file, mime_type)
            return self._perform(files=files)

    def upload_urls(self, *urls):
        """ Upload image URLs by downloading them before """
        with contextlib.ExitStack() as stack:
            files = {}
            for i, url in enumerate(urls):
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code != 200:
                    raise ValueError(
                        'Cannot fetch url {} with error {}'.format(url, resp.status_code))
                mime_type = resp.headers['content-type']
                if not mime_type or mime_type.split('/')[0] != 'image':
                    raise ValueError(
                        'Unknown image file type {}'.format(mime_type))
                open_file = stack.enter_context(BytesIO(resp.content))
                files['file-upload[{}]'.format(i)] = (
                    'file-{}'.format(i), open_file, mime_type)

            return self._perform(files=files)

def _partition(files_or_urls):
    files, urls = [], []
    for file_or_url in files_or_urls:
        if os.path.exists(file_or_url):
            files.append(file_or_url)
        elif file_or_url.startswith('http'):
            urls.append(file_or_url)
        else:
            raise ValueError(
                'Not an existing file or image URL: {}'.format(file_or_url))
    return files, urls

def upload(api_key, files_or_urls, timeout=None):
    uploader = PtpimgUploader(api_key, timeout)
    files, urls = _partition(files_or_urls)
    results = []
    if files:
        results += uploader.upload_files(*files)
    if urls:
        results += uploader.upload_urls(*urls)
    return results

def main():
    import argparse

    try:
        import pyperclip
    except ImportError:
        pyperclip = None

    parser = argparse.ArgumentParser(description="PTPImg uploader")
    parser.add_argument('images', metavar='filename|url', nargs='+')
    parser.add_argument(
        '-k', '--api-key', default=os.environ.get('PTPIMG_API_KEY'),
        help='PTPImg API key (or set the PTPIMG_API_KEY environment variable)')
    if pyperclip is not None:
        parser.add_argument(
            '-n', '--dont-copy', action='store_false', default=True,
            dest='clipboard',
            help='Do not copy the resulting URLs to the clipboard')
    parser.add_argument(
        '-b', '--bbcode', action='store_true', default=False,
        help='Output links in BBCode format (with [img] tags)')
    parser.add_argument(
        '--nobell', action='store_true', default=False,
        help='Do not bell in a terminal on completion')
    parser.add_argument(
        '-m', '--media', action='store_true', default=False,
        help='Print mediainfo alongwith urls (with tags)'        
    )
    args = parser.parse_args()

    if not args.api_key:
        parser.error('Please specify an API key')
    try:
        fname=None
        ss=getscreenshot()
        image_urls = upload(args.api_key, ss)
        if args.bbcode:
            printed_urls = ['[img]{}[/img]'.format(image_url) for image_url in image_urls]
        if args.media:
            outMsg = ""   
            outMsg += f"[size=4]{getFilename(fname)}[/size]"
            outMsg += "[hr]"
            outMsg += f"[mediainfo]{getMediainfo(fname)}[/mediainfo]"
            outMsg += "[hr]"
            print(outMsg)
        print(*printed_urls, sep='\n')
        # Copy to clipboard if possible
        if getattr(args, 'clipboard', False):
            pyperclip.copy(outMsg,'\n'.join(printed_urls))
        # Ring a terminal if we are in terminal and allowed to do this
        if not args.nobell and sys.stdout.isatty():
            sys.stdout.write('\a')
            sys.stdout.flush()
    except (UploadFailed, ValueError) as e:
        parser.error(str(e))

    check=input("Do you want to delete the screenshots?\nResponse:[y/n]")
    if check=="y":
        folder_fname = os.getcwd()
        for file_name in os.listdir(folder_fname):
            if file_name.startswith('img'):
                os.remove(folder_fname+"\\"+file_name)
        print("_"*50)
        print("Files uploaded to above urls\nAll screenshots were deleted.")
    else:
        print("_"*50)
        print("Files uploaded to above urls")

if __name__ == '__main__':
    main()
