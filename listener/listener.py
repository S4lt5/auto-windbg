# C:\Users\Offsec\AppData\Local\Programs\Python\Python37-32\python.exe listener.py
# put bottle.py in the same root
from bottle import route, run, template, response, HTTPResponse, post, request
import os
import ctypes
import uuid

from subprocess import check_output, Popen

debugger_proc = None
windbg_options = "-WF C:\\windbg_custom.WEW"
scratch_path = "C:/windows/temp"


def isAdmin():
    try:
        is_admin = (os.getuid() == 0)
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    return is_admin


@route('/debugger/healthcheck')
def healthCheck():
    admin = isAdmin()
    if admin:
        return HTTPResponse(body="All is well!")

    return HTTPResponse(status=500, body="I am not admin :(")


@route('/debugger/detach', method='POST')
def detach():
    try:
        global debugger_proc
        if debugger_proc == None:
            raise ("Process does not exist")
        debugger_proc.kill()
        debugger_proc = None
        return HTTPResponse(body="Success")

    except Exception as err:
        return HTTPResponse(status=500, body=err)


def make_temp_file(file_name, contents):
    with open(file_name, 'w') as f:
        f.writelines(contents)
        f.flush()
        f.close()


@route('/debugger/retrieve', method='GET')
def do_retrieve():
    try:
        global scratch_path
        receipt_id = request.forms.get('receipt_id')
        if receipt_id is None:
            raise Exception("No receipt was presented")

        # you can see how this would be pretty insecure...
        output_path = os.path.join(scratch_path, receipt_id+".out")
        contents = ""
        with open(output_path, 'r') as f:
            contents = f.read()

        return HTTPResponse(body=contents)

    except Exception as err:
        print("Something went wrong!")
        print(err)
        return HTTPResponse(status=500, body=err)


@route('/debugger/attach', method='POST')
def do_attach():
    try:

        global debugger_proc
        global windbg_options
        global scratch_path

        # if debugger_proc != None:
        # raise Exception("Process already running")
        process_name = request.forms.get('process_name')

        # get a unique receipt ID incase we need it for returning data
        receipt_id = str(uuid.uuid4())

        location = request.forms.get('location')
        # divide bytes by wordsize
        length = int(request.forms.get('length'))
        # add some bytes just in case we miss it on the end
        length = int(length)+8
        # if we're examining a location
        temp_location = os.path.join(scratch_path, receipt_id)
        if location is not None:

            lines = [
                "import pykd\n",
                "\n",
                f'resp = pykd.dbgCommand("db {location} L{length}")\n',
                f'file = open("{scratch_path}/{receipt_id}.out","w")\n',
                'file.write(resp)\n',
                'file.close()\n',
                f'print("DONE! Wrote to {scratch_path}/{receipt_id}.out")\n'
            ]
            make_temp_file(file_name=f"{temp_location}.py", contents=lines)

        # with shell=True, process kill does not work
        debugger_proc = Popen(
            ["C:\\Program Files\\Windows Kits\\10\\Debuggers\\x86\\WinDbg.exe", "-WF",
             "C:\\windbg_custom.WEW", "-g", "-pn",
             process_name, "/c", f".load pykd;!info;!py {temp_location}.py "], shell=False)
        return HTTPResponse(body=str(receipt_id))
    except Exception as err:
        print("Something went wrong!")
        print(err)
        return HTTPResponse(status=500, body=err)


@route('/debugger/run', method='POST')
def do_run():
    try:
        print("Entering run")
        cmd = request.forms.get('cmd')
        background = request.forms.get('background')
        print(cmd)
        pid = ""
        if background == "True":
            pid = Popen(cmd, shell=False)
        else:
            check_output(cmd, shell=True)
        return HTTPResponse()
    except Exception as err:
        print(err)
        return HTTPResponse(status=500, body=err)


run(host='192.168.166.10', port=5353)