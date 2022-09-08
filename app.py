#!/usr/bin/env python
# -*- coding:utf-8 -*-
import json
import os
import time

import requests
from flask import Flask, flash, request, redirect, render_template,Response,url_for
from ops_channel import cli
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret key"
UPLOAD_FOLDER = './upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

from queue import Queue

import threading

ALLOWED_EXTENSIONS = set(['graphqls'])

GRAPHQLS = {

}

Q = Queue()


QUERY={
    "query": "\n    query IntrospectionQuery {\n      __schema {\n        \n        queryType { name }\n        mutationType { name }\n        subscriptionType { name }\n        types {\n          ...FullType\n        }\n        directives {\n          name\n          description\n          \n          locations\n          args {\n            ...InputValue\n          }\n        }\n      }\n    }\n\n    fragment FullType on __Type {\n      kind\n      name\n      description\n      \n      fields(includeDeprecated: true) {\n        name\n        description\n        args {\n          ...InputValue\n        }\n        type {\n          ...TypeRef\n        }\n        isDeprecated\n        deprecationReason\n      }\n      inputFields {\n        ...InputValue\n      }\n      interfaces {\n        ...TypeRef\n      }\n      enumValues(includeDeprecated: true) {\n        name\n        description\n        isDeprecated\n        deprecationReason\n      }\n      possibleTypes {\n        ...TypeRef\n      }\n    }\n\n    fragment InputValue on __InputValue {\n      name\n      description\n      type { ...TypeRef }\n      defaultValue\n      \n      \n    }\n\n    fragment TypeRef on __Type {\n      kind\n      name\n      ofType {\n        kind\n        name\n        ofType {\n          kind\n          name\n          ofType {\n            kind\n            name\n            ofType {\n              kind\n              name\n              ofType {\n                kind\n                name\n                ofType {\n                  kind\n                  name\n                  ofType {\n                    kind\n                    name\n                  }\n                }\n              }\n            }\n          }\n        }\n      }\n    }\n  ",
    "operationName": "IntrospectionQuery"
}


def load_schema():
    if os.path.exists(os.path.join('graph/schema.json')):
        with open(os.path.join('graph/schema.json'),'r') as fp:
            GRAPHQLS.update(json.loads(fp.read()))
load_schema()

def consumer():
    while True:
        try:
            item = Q.get()
            if item is None:
                time.sleep(1)
                continue
            with open('./graph/schema.graphqls', 'w') as f:
                f.write(item['schemas'])
            shell = b'''
            cd /app/gqlmock
            rm -rf ./graph/schema.resolvers.go 
            gqlgen
            go run server.go
            '''
            # print(cli.execute_shell(shell))
            t = threading.Thread(target=cli.execute_shell, args=(shell,60,))
            t.setDaemon(True)
            t.start()
            timeout = 0
            while True:
                try:
                    timeout = timeout + 1
                    time.sleep(1)
                    if cli.check_port(port=8080):
                        data = requests.post('http://127.0.0.1:8080/query', json=QUERY).json()
                        GRAPHQLS[item['project']] = {'data': data, 'schemas': item['schemas']}
                        with open(os.path.join('graph/schema.json'),'w') as fp:
                            fp.write(json.dumps(GRAPHQLS))
                        requests.get('http://127.0.0.1:8080/exit')
                        break
                    else:
                        if timeout > 30:
                            break
                except Exception as e:
                    print('error',e)
                    break
        except Exception as er:
            print(er)
            time.sleep(1)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def upload_form():
    return render_template('upload.html',url_root=request.url_root)


@app.route('/schema')
def get_schema():
    project = request.args.get('project')
    data= GRAPHQLS.get(project)
    if data is not None:
        return Response(data['schemas'], mimetype='text/plain')
    else:
        return 'not found'

@app.route('/query')
def query():
    project = request.args.get('project')
    data= GRAPHQLS.get(project)
    if data is not None:
        return data['data']
    else:
        return 'not found'

@cli.try_except()
@app.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the files part
        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)
        with open(os.path.join("graph/schema.graphqls"), 'w') as f:
            files = request.files.getlist('files[]')
            schemas = []
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    schemas.append(file.read().decode('utf-8'))
                # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # flash('File(s) successfully uploaded')
        Q.put({'project': request.form.get('project'), 'schemas': "\n".join(schemas)})
        return redirect('/?project='+request.form['project'])


if __name__ == "__main__":
    t = threading.Thread(target=consumer)
    t.setDaemon(True)
    t.start()
    app.run(host='0.0.0.0',debug=True)
