"""
CLOUDSNARE Agent — tool schemas.

These describe each tool to the LLM in the structured format the Anthropic
API's tool-use feature expects. The model reads these and, instead of free
text, returns a request to call one specific tool with specific parameters.

The model literally cannot return anything outside this menu — that is the
core safety property. If a required field is missing, the model asks the user
for it (a follow-up question) rather than guessing.
"""

TOOL_SCHEMAS = [
    {
        "name": "list_buckets",
        "description": "List the S3 buckets in the account. Read-only.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_instances",
        "description": "List the EC2 instances in the account. Read-only.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_secure_bucket",
        "description": (
            "Create a new S3 bucket that is private, encrypted, and versioned "
            "by default. Use when the user wants storage for files/data. The "
            "bucket is ALWAYS private and secure — there is no option to make "
            "it public."),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Globally-unique bucket name (lowercase, "
                                   "hyphens ok, no spaces). Ask the user if unknown."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "create_secure_ec2",
        "description": (
            "Launch a new EC2 instance with a locked-down security group (no "
            "inbound internet access) and no public IP. Use when the user wants "
            "a server or compute. Defaults to a Free-Tier t2.micro. Warn that it "
            "costs money and should be terminated when done."),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "A name/tag for the instance. Ask if unknown."},
                "instance_type": {
                    "type": "string",
                    "description": "EC2 instance type. Default t2.micro (Free Tier). "
                                   "Only change if the user explicitly asks."},
            },
            "required": ["name"],
        },
    },
]

SYSTEM_PROMPT = (
    "You are the CLOUDSNARE cloud assistant. You help people — including those "
    "with no cloud experience — provision AWS resources safely through "
    "conversation. You can only act through the provided tools; you never run "
    "arbitrary commands. Everything you create is secure by default (private, "
    "encrypted, locked down).\n\n"
    "Rules:\n"
    "- If a tool needs information you don't have (like a bucket name), ASK the "
    "user a brief follow-up question instead of guessing.\n"
    "- Before creating anything, clearly state what you're about to do in plain "
    "language. The system will then ask the user to confirm.\n"
    "- For EC2, always remind the user it costs money and should be terminated "
    "when finished.\n"
    "- Be concise and friendly. Explain things simply for non-experts."
)
