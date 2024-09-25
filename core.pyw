# core.py

import requests
import yaml
import json
import os

def fetch_spec(url):
    """
    Fetches and parses the OpenAPI specification from the given URL.
    Supports JSON and YAML formats.
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch specification from {url} (Status code: {response.status_code})")
    
    content_type = response.headers.get('Content-Type', '').lower()
    text = response.text

    if 'application/json' in content_type or url.endswith('.json'):
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON specification: {e}")
    elif 'application/yaml' in content_type or 'application/x-yaml' in content_type or url.endswith(('.yaml', '.yml')):
        try:
            spec = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise Exception(f"Failed to parse YAML specification: {e}")
    else:
        # Try JSON first, then YAML
        try:
            spec = json.loads(text)
        except json.JSONDecodeError:
            try:
                spec = yaml.safe_load(text)
            except yaml.YAMLError as e:
                raise Exception(f"Failed to parse specification as JSON or YAML: {e}")
    
    return spec

def list_endpoints(spec):
    """
    Extracts all endpoints from the OpenAPI specification.
    Returns a list of dictionaries containing method, path, summary, operationId, and parameters.
    """
    endpoints = []
    paths = spec.get('paths', {})
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                continue  # Skip invalid HTTP methods
            summary = operation.get('summary', '')
            parameters = operation.get('parameters', [])
            endpoints.append({
                'method': method.upper(),
                'path': path,
                'summary': summary,
                'operationId': operation.get('operationId', ''),
                'parameters': parameters
            })
    return endpoints

def generate_script(spec, endpoint, param_values, language='Python'):
    """
    Generates code to interact with the given endpoint in the specified language.
    Returns the generated code as a string.
    """
    servers = spec.get('servers', [])
    if servers:
        base_url = servers[0]['url']
    else:
        # For Swagger 2.0, use host and basePath
        host = spec.get('host', '')
        base_path = spec.get('basePath', '')
        schemes = spec.get('schemes', ['https'])
        base_url = f"{schemes[0]}://{host}{base_path}"

    method = endpoint['method'].lower()
    path = endpoint['path']
    operation = spec['paths'][path][method]

    # Prepare URL
    url = base_url + path
    path_params = []
    query_params = {}
    header_params = {}
    body_param = None
    form_params = {}

    # Handle parameters
    parameters = operation.get('parameters', [])
    for param in parameters:
        name = param['name']
        value = param_values.get(name, '')
        if param['in'] == 'path':
            path_params.append((name, value))
        elif param['in'] == 'query':
            query_params[name] = value
        elif param['in'] == 'header':
            header_params[name] = value
        elif param['in'] == 'body':
            body_param = value
        elif param['in'] == 'formData':
            form_params[name] = value

    # Replace path parameters in URL
    for name, value in path_params:
        url = url.replace(f"{{{name}}}", str(value))

    # Generate code based on language
    if language == 'Python':
        return generate_python_code(url, method, query_params, header_params, body_param, form_params)
    elif language == 'C#':
        return generate_csharp_code(url, method, query_params, header_params, body_param, form_params)
    elif language == 'JavaScript':
        return generate_javascript_code(url, method, query_params, header_params, body_param, form_params)
    elif language == 'PHP':
        return generate_php_code(url, method, query_params, header_params, body_param, form_params)
    else:
        raise Exception(f"Unsupported language: {language}")

def generate_python_code(url, method, query_params, header_params, body_param, form_params):
    code = "import requests\n\n"
    code += f"url = '{url}'\n"
    if query_params:
        code += f"params = {json.dumps(query_params)}\n"
    else:
        code += "params = {}\n"
    if header_params:
        code += f"headers = {json.dumps(header_params)}\n"
    else:
        code += "headers = {}\n"
    if body_param:
        code += f"json_body = {body_param}\n"
    else:
        code += "json_body = None\n"
    if form_params:
        code += f"data = {json.dumps(form_params)}\n"
    else:
        code += "data = None\n"
    code += f"response = requests.{method}(\n"
    code += "    url,\n"
    code += "    params=params,\n"
    code += "    headers=headers,\n"
    if body_param:
        code += "    json=json_body,\n"
    if form_params:
        code += "    data=data,\n"
    code += ")\n"
    code += "print('Status Code:', response.status_code)\n"
    code += "print('Response Body:', response.text)\n"
    return code

def generate_csharp_code(url, method, query_params, header_params, body_param, form_params):
    # Using HttpClient in C#
    code = "using System;\nusing System.Net.Http;\nusing System.Threading.Tasks;\nusing Newtonsoft.Json;\n\n"
    code += "class Program\n{\n"
    code += "    static async Task Main(string[] args)\n    {\n"
    code += "        var client = new HttpClient();\n"
    code += f"        var url = \"{url}\";\n"
    if query_params:
        query_string = '&'.join(f"{k}={v}" for k, v in query_params.items())
        code += f"        url += \"?{query_string}\";\n"
    if header_params:
        for k, v in header_params.items():
            code += f"        client.DefaultRequestHeaders.Add(\"{k}\", \"{v}\");\n"
    if body_param:
        code += f"        var jsonBody = {body_param};\n"
        code += "        var content = new StringContent(JsonConvert.SerializeObject(jsonBody), System.Text.Encoding.UTF8, \"application/json\");\n"
    elif form_params:
        code += "        var content = new FormUrlEncodedContent(new[]\n        {\n"
        for k, v in form_params.items():
            code += f"            new KeyValuePair<string, string>(\"{k}\", \"{v}\"),\n"
        code += "        });\n"
    else:
        code += "        HttpContent content = null;\n"
    code += f"        var response = await client.{method.capitalize()}Async(url, content);\n"
    code += "        var responseString = await response.Content.ReadAsStringAsync();\n"
    code += "        Console.WriteLine($\"Status Code: {response.StatusCode}\");\n"
    code += "        Console.WriteLine($\"Response Body: {responseString}\");\n"
    code += "    }\n}\n"
    return code

def generate_javascript_code(url, method, query_params, header_params, body_param, form_params):
    # Using Fetch API in JavaScript
    code = "const fetch = require('node-fetch');\n\n"
    code += f"let url = '{url}';\n"
    if query_params:
        query_string = '&'.join(f"{k}={v}" for k, v in query_params.items())
        code += f"url += '?{query_string}';\n"
    code += "const options = {\n"
    code += f"    method: '{method.upper()}',\n"
    if header_params:
        code += "    headers: {\n"
        for k, v in header_params.items():
            code += f"        '{k}': '{v}',\n"
        code += "    },\n"
    if body_param:
        code += f"    body: JSON.stringify({body_param}),\n"
    elif form_params:
        code += "    body: new URLSearchParams({\n"
        for k, v in form_params.items():
            code += f"        '{k}': '{v}',\n"
        code += "    }),\n"
    code += "};\n"
    code += "fetch(url, options)\n"
    code += "    .then(response => response.text())\n"
    code += "    .then(text => {\n"
    code += "        console.log('Response Body:', text);\n"
    code += "    })\n"
    code += "    .catch(err => console.error('Error:', err));\n"
    return code

def generate_php_code(url, method, query_params, header_params, body_param, form_params):
    code = "<?php\n"
    code += "$ch = curl_init();\n"
    if query_params:
        query_string = '&'.join(f"{k}={v}" for k, v in query_params.items())
        code += f"$url = '{url}?{query_string}';\n"
    else:
        code += f"$url = '{url}';\n"
    code += f"curl_setopt($ch, CURLOPT_URL, $url);\n"
    code += f"curl_setopt($ch, CURLOPT_CUSTOMREQUEST, '{method.upper()}');\n"
    code += "curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);\n"
    if header_params:
        code += "$headers = [\n"
        for k, v in header_params.items():
            code += f"    '{k}: {v}',\n"
        code += "];\n"
        code += "curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);\n"
    if body_param:
        code += f"$data = json_encode({body_param});\n"
        code += "curl_setopt($ch, CURLOPT_POSTFIELDS, $data);\n"
    elif form_params:
        code += "$data = http_build_query([\n"
        for k, v in form_params.items():
            code += f"    '{k}' => '{v}',\n"
        code += "]);\n"
        code += "curl_setopt($ch, CURLOPT_POSTFIELDS, $data);\n"
    code += "$response = curl_exec($ch);\n"
    code += "curl_close($ch);\n"
    code += "echo 'Response Body: ' . $response;\n"
    code += "?>\n"
    return code

def save_script(code, filename):
    """
    Saves the generated code to a file.
    """
    with open(filename, 'w') as file:
        file.write(code)
