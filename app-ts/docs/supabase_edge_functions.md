### Managing dependencies

Managing packages and dependencies.

Importing dependencies#
Supabase Edge Functions support several ways to import dependencies:

JavaScript modules from npm (https://docs.deno.com/examples/npm/)
Built-in Node APIs
Modules published to JSR or deno.land/x
NPM modules#
You can import npm modules using the npm: specifier:

```import { createClient } from 'npm:@supabase/supabase-js@2'
```
Node.js built-ins#
For Node.js built-in APIs, use the node: specifier:

```import process from 'node:process'```
Learn more about npm specifiers and Node built-in APIs in Deno's documentation.

JSR#
You can import JS modules published to JSR (e.g.: Deno's standard library), using the jsr: specifier:

```import path from 'jsr:@std/path@1.0.8'
```
Managing dependencies#
Developing with Edge Functions is similar to developing with Node.js, but with a few key differences.

In the Deno ecosystem, each function should be treated as an independent project with its own set of dependencies and configurations. This "isolation by design" approach:

Ensures each function has explicit control over its dependencies
Prevents unintended side effects between functions
Makes deployments more predictable and maintainable
Allows for different versions of the same dependency across functions
For these reasons, we recommend maintaining separate configuration files (deno.json, .npmrc, or import_map.json) within each function's directory, even if it means duplicating some configurations.

There are two ways to manage your dependencies in Supabase Edge Functions:

Using deno.json (recommended)#
This feature requires Supabase CLI version 1.215.0 or higher.

Each function should have its own deno.json file to manage dependencies and configure Deno-specific settings. This ensures proper isolation between functions and is the recommended approach for deployment. For a complete list of supported options, see the official Deno configuration documentation.

```{
  "imports": {
    "lodash": "https://cdn.skypack.dev/lodash"
  }
}```
The recommended file structure for deployment:

```└── supabase
    ├── functions
    │   ├── function-one
    │   │   ├── index.ts
    │   │   ├─- deno.json    # Function-specific Deno configuration
    │   │   └── .npmrc       # Function-specific npm configuration (if needed)
    │   └── function-two
    │       ├── index.ts
    │       ├─- deno.json    # Function-specific Deno configuration
    │       └── .npmrc       # Function-specific npm configuration (if needed)
    └── config.toml```

While it's possible to use a global deno.json in the /supabase/functions directory for local
development, this approach is not recommended for deployment. Each function should maintain its
own configuration to ensure proper isolation and dependency management.

Using import maps (legacy)#
Import Maps are a legacy way to manage dependencies, similar to a package.json file. While still supported, we recommend using deno.json. If both exist, deno.json takes precedence.

Each function should have its own import_map.json file for proper isolation:

```{
  "imports": {
    "lodash": "https://cdn.skypack.dev/lodash"
  }
}```
The recommended file structure:

```└── supabase
    ├── functions
    │   ├── function-one
    │   │   ├── index.ts
    │   │   └── import_map.json    # Function-specific import map
    │   └── function-two
    │       ├── index.ts
    │       └── import_map.json    # Function-specific import map
    └── config.toml```
While it's possible to use a global import_map.json in the /supabase/functions directory for
local development, this approach is not recommended for deployment. Each function should maintain
its own import map to ensure proper isolation.

If using import maps with VSCode, update your .vscode/settings.json to point to your function-specific import map:

```{
  "deno.enable": true,
  "deno.unstable": [
    "bare-node-builtins",
    "byonm"
    // ... other flags ...
  ],
  "deno.importMap": "./supabase/functions/my-function/import_map.json"
}```
You can override the default import map location using the --import-map <string> flag with serve and deploy commands, or by setting the import_map property in your config.toml file:

```[functions.my-function]
import_map = "./supabase/functions/my-function/import_map.json"```
Importing from private registries#
This feature requires Supabase CLI version 1.207.9 or higher.
To use private npm packages, create a .npmrc file within your function directory. This ensures proper isolation and dependency management for each function.

```└── supabase
    └── functions
        └── my-function
            ├── index.ts
            ├── deno.json
            └── .npmrc       # Function-specific npm configuration```
Add your registry details in the .npmrc file. Follow this guide to learn more about the syntax of npmrc files.

@myorg:registry=https://npm.registryhost.com
//npm.registryhost.com/:_authToken=VALID_AUTH_TOKEN
While it's possible to use a global .npmrc in the /supabase/functions directory for local
development, we recommend using function-specific .npmrc files for deployment to maintain proper
isolation.

After configuring your .npmrc, you can import the private package in your function code:

import MyPackage from 'npm:@myorg/private-package@v1.0.1'
// use MyPackage
Using a custom NPM registry#
This feature requires Supabase CLI version 2.2.8 or higher.
Some organizations require a custom NPM registry for security and compliance purposes. In such instances, you can specify the custom NPM registry to use via NPM_CONFIG_REGISTRY environment variable.

You can define it in the project's .env file or directly specify it when running the deploy command:

NPM_CONFIG_REGISTRY=https://custom-registry/ supabase functions deploy my-function
Importing types#
If your environment is set up properly and the module you're importing is exporting types, the import will have types and autocompletion support.

Some npm packages may not ship out of the box types and you may need to import them from a separate package. You can specify their types with a @deno-types directive:

// @deno-types="npm:@types/express@^4.17"
import express from 'npm:express@^4.17'
To include types for built-in Node APIs, add the following line to the top of your imports:

/// <reference types="npm:@types/node" />


---


###Background Tasks

How to run background tasks in an Edge Function outside of the request handler

Edge Function instances can process background tasks outside of the request handler. Background tasks are useful for asynchronous operations like uploading a file to Storage, updating a database, or sending events to a logging service. You can respond to the request immediately and leave the task running in the background.

How it works#
You can use EdgeRuntime.waitUntil(promise) to explicitly mark background tasks. The Function instance continues to run until the promise provided to waitUntil completes.

The maximum duration is capped based on the wall-clock, CPU, and memory limits. The Function will shutdown when it reaches one of these limits.

You can listen to the beforeunload event handler to be notified when Function invocation is about to be shut down.

Example#
Here's an example of using EdgeRuntime.waitUntil to run a background task and using beforeunload event to be notified when the instance is about to be shut down.

```async function longRunningTask() {
  // do work here
}
// Mark the longRunningTask's returned promise as a background task.
// note: we are not using await because we don't want it to block.
EdgeRuntime.waitUntil(longRunningTask())
// Use beforeunload event handler to be notified when function is about to shutdown
addEventListener('beforeunload', (ev) => {
  console.log('Function will be shutdown due to', ev.detail?.reason)
  // save state or log the current progress
})
// Invoke the function using a HTTP request.
// This will start the background task
Deno.serve(async (req) => {
  return new Response('ok')
})```
Starting a background task in the request handler#
You can call EdgeRuntime.waitUntil in the request handler too. This will not block the request.

```async function fetchAndLog(url: string) {
  const response = await fetch(url)
  console.log(response)
}
Deno.serve(async (req) => {
  // this will not block the request,
  // instead it will run in the background
  EdgeRuntime.waitUntil(fetchAndLog('https://httpbin.org/json'))
  return new Response('ok')
})```
Testing background tasks locally#
When testing Edge Functions locally with Supabase CLI, the instances are terminated automatically after a request is completed. This will prevent background tasks from running to completion.

To prevent that, you can update the supabase/config.toml with the following settings:
```
[edge_runtime]
policy = "per_worker"
```
When running with per_worker policy, Function won't auto-reload on edits. You will need to manually restart it by running supabase functions serve.

---

### Managing Secrets (Environment Variables)

Managing secrets and environment variables.

It's common that you will need to use environment variables or other sensitive information Edge Functions. You can manage secrets using the CLI or the Dashboard.

You can access these using Deno's built-in handler

Deno.env.get('MY_SECRET_NAME')
Default secrets#
Edge Functions have access to these secrets by default:

SUPABASE_URL: The API gateway for your Supabase project.
SUPABASE_ANON_KEY: The anon key for your Supabase API. This is safe to use in a browser when you have Row Level Security enabled.
SUPABASE_SERVICE_ROLE_KEY: The service_role key for your Supabase API. This is safe to use in Edge Functions, but it should NEVER be used in a browser. This key will bypass Row Level Security.
SUPABASE_DB_URL: The URL for your Postgres database. You can use this to connect directly to your database.
Local secrets#
You can load environment variables in two ways:

Through an .env file placed at supabase/functions/.env, which is automatically loaded on supabase start
Through the --env-file option for supabase functions serve, for example: supabase functions serve --env-file ./path/to/.env-file
Let's create a local file for storing our secrets, and inside it we can store a secret MY_NAME:

echo "MY_NAME=Yoda" >> ./supabase/.env.local
This creates a new file ./supabase/.env.local for storing your local development secrets.

Never check your .env files into Git!

Now let's access this environment variable MY_NAME inside our Function. Anywhere in your function, add this line:

console.log(Deno.env.get('MY_NAME'))
Now we can invoke our function locally, by serving it with our new .env.local file:

supabase functions serve --env-file ./supabase/.env.local
When the function starts you should see the name “Yoda” output to the terminal.

Production secrets#
You will also need to set secrets for your production Edge Functions. You can do this via the Dashboard or using the CLI.

Using the Dashboard#
Visit Edge Function Secrets Management page in your Dashboard.
Add the Key and Value for your secret and press Save.
Note that you can paste multiple secrets at a time.
Edge Functions Secrets Management
Using the CLI#
Let's create a .env to help us deploy our secrets to production. In this case we'll just use the same as our local secrets:

cp ./supabase/.env.local ./supabase/.env
This creates a new file ./supabase/.env for storing your production secrets.

Never check your .env files into Git! You only use the .env file to help deploy your secrets to production. Don't commit it to your repository.

Let's push all the secrets from the .env file to our remote project using supabase secrets set:

supabase secrets set --env-file ./supabase/.env
# You can also set secrets individually using:
supabase secrets set MY_NAME=Chewbacca
You don't need to re-deploy after setting your secrets.

To see all the secrets which you have set remotely, use supabase secrets list:

supabase secrets list

---



### Connecting directly to Postgres

Connecting to Postgres from Edge Functions.

Connect to your Postgres database from an Edge Function by using the supabase-js client.
You can also use other Postgres clients like Deno Postgres

Using supabase-js#
The supabase-js client is a great option for connecting to your Supabase database since it handles authorization with Row Level Security, and it automatically formats your response as JSON.

import { createClient } from 'jsr:@supabase/supabase-js@2'
Deno.serve(async (req) => {
  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: req.headers.get('Authorization')! } } }
    )
    const { data, error } = await supabase.from('countries').select('*')
    if (error) {
      throw error
    }
    return new Response(JSON.stringify({ data }), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    })
  } catch (err) {
    return new Response(String(err?.message ?? err), { status: 500 })
  }
})
Using a Postgres client#
Because Edge Functions are a server-side technology, it's safe to connect directly to your database using any popular Postgres client. This means you can run raw SQL from your Edge Functions.

Here is how you can connect to the database using Deno Postgres driver and run raw SQL.

Check out the full example.

import * as postgres from 'https://deno.land/x/postgres@v0.17.0/mod.ts'
// Get the connection string from the environment variable "SUPABASE_DB_URL"
const databaseUrl = Deno.env.get('SUPABASE_DB_URL')!
// Create a database pool with three connections that are lazily established
const pool = new postgres.Pool(databaseUrl, 3, true)
Deno.serve(async (_req) => {
  try {
    // Grab a connection from the pool
    const connection = await pool.connect()
    try {
      // Run a query
      const result = await connection.queryObject`SELECT * FROM animals`
      const animals = result.rows // [{ id: 1, name: "Lion" }, ...]
      // Encode the result as pretty printed JSON
      const body = JSON.stringify(
        animals,
        (key, value) => (typeof value === 'bigint' ? value.toString() : value),
        2
      )
      // Return the response with the correct content type header
      return new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
      })
    } finally {
      // Release the connection back into the pool
      connection.release()
    }
  } catch (err) {
    console.error(err)
    return new Response(String(err?.message ?? err), { status: 500 })
  }
})
Using Drizzle#
You can use Drizzle together with Postgres.js. Both can be loaded directly from npm:

{
  "imports": {
    "drizzle-orm": "npm:drizzle-orm@0.29.1",
    "drizzle-orm/": "npm:/drizzle-orm@0.29.1/",
    "postgres": "npm:postgres@3.4.3"
  }
}
import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import { countries } from '../_shared/schema.ts'
const connectionString = Deno.env.get('SUPABASE_DB_URL')!
Deno.serve(async (_req) => {
  // Disable prefetch as it is not supported for "Transaction" pool mode
  const client = postgres(connectionString, { prepare: false })
  const db = drizzle(client)
  const allCountries = await db.select().from(countries)
  return Response.json(allCountries)
})
You can find the full example on GitHub.

SSL connections#
Deployed edge functions are pre-configured to use SSL for connections to the Supabase database. You don't need to add any extra configurations.

If you want to use SSL connections during local development, follow these steps:

Download the SSL certificate from Database settings

In your local .env file, add these two variables:

SSL_CERT_FILE=/path/to/cert.crt # set the path to the downloaded cert
DENO_TLS_CA_STORE=mozilla,system



---



### Handling Routing in Functions

How to handle custom routing within Edge Functions.

Usually, an Edge Function is written to perform a single action (e.g. write a record to the database). However, if your app's logic is split into multiple Edge Functions requests to each action may seem slower.
This is because each Edge Function needs to be booted before serving a request (known as cold starts). If an action is performed less frequently (e.g. deleting a record), there is a high-chance of that function experiencing a cold-start.

One way to reduce the cold starts and increase performance of your app is to combine multiple actions into a single Edge Function. This way only one instance of the Edge Function needs to be booted and it can handle multiple requests to different actions.
For example, we can use a single Edge Function to create a typical CRUD API (create, read, update, delete records).

To combine multiple endpoints into a single Edge Function, you can use web application frameworks such as Express, Oak, or Hono.

Let's dive into some examples.

Routing with frameworks#
Here's a simple hello world example using some popular web frameworks.

Create a new function called hello-world using Supabase CLI:

supabase functions new hello-world
Copy and paste the following code:


Express


import express from 'npm:express@4.18.2'
const app = express()
app.use(express.json())
// If you want a payload larger than 100kb, then you can tweak it here:
// app.use( express.json({ limit : "300kb" }));
const port = 3000
app.get('/hello-world', (req, res) => {
  res.send('Hello World!')
})
app.post('/hello-world', (req, res) => {
  const { name } = req.body
  res.send(`Hello ${name}!`)
})
app.listen(port, () => {
  console.log(`Example app listening on port ${port}`)
})
You will notice in the above example, we created two routes - GET and POST. The path for both routes are defined as /hello-world.
If you run a server outside of Edge Functions, you'd usually set the root path as / .
However, within Edge Functions, paths should always be prefixed with the function name (in this case hello-world).

You can deploy the function to Supabase via:

supabase functions deploy hello-world
Once the function is deployed, you can try to call the two endpoints using cURL (or Postman).

# https://supabase.com/docs/guides/functions/deploy#invoking-remote-functions
curl --request GET 'https://<project_ref>.supabase.co/functions/v1/hello-world' \
  --header 'Authorization: Bearer ANON_KEY' \
This should print the response as Hello World!, meaning it was handled by the GET route.

Similarly, we can make a request to the POST route.

# https://supabase.com/docs/guides/functions/deploy#invoking-remote-functions
curl --request POST 'https://<project_ref>.supabase.co/functions/v1/hello-world' \
  --header 'Authorization: Bearer ANON_KEY' \
  --header 'Content-Type: application/json' \
  --data '{ "name":"Foo" }'
We should see a response printing Hello Foo!.

Using route parameters#
We can use route parameters to capture values at specific URL segments (e.g. /tasks/:taskId/notes/:noteId).

Here's an example Edge Function implemented using the Framework for managing tasks using route parameters.
Keep in mind paths must be prefixed by function name (i.e. tasks in this example). Route parameters can only be used after the function name prefix.


Express


import express from 'npm:express@4.18.2'
const app = express();
app.use(express.json());
app.get('/tasks', async (req, res) => {
// return all tasks
});
app.post('/tasks', async (req, res) => {
// create a task
});
app.get('/tasks/:id', async (req, res) => {
const id = req.params.id
const task = {} // get task
res.json(task)
});
app.patch('/tasks/:id', async (req, res) => {
const id = req.params.id
// modify task
});
app.delete('/tasks/:id', async (req, res) => {
const id = req.params.id
// delete task
});
URL patterns API#
If you prefer not to use a web framework, you can directly use URL Pattern API within your Edge Functions to implement routing.
This is ideal for small apps with only couple of routes and you want to have a custom matching algorithm.

Here is an example Edge Function using URL Patterns API: https://github.com/supabase/supabase/blob/master/examples/edge-functions/supabase/functions/restful-tasks/index.ts

