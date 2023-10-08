# Copyright (c) Microsoft. All rights reserved.

import asyncio
import boto3
from datetime import datetime
import uuid
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = 'Chat'  # Replace with your DynamoDB table name
conversation_history_table = dynamodb.Table(table_name)

sk_prompt = """
ChatBot can have a conversation with you about any topic.
It can give explicit instructions or say 'I don't know'
when it doesn't know the answer.

{{$chat_history}}
User:> {{$user_input}}
ChatBot:>
"""

kernel = sk.Kernel()

api_key, org_id = sk.openai_settings_from_dot_env()
kernel.add_chat_service(
    "chat-gpt", OpenAIChatCompletion("gpt-3.5-turbo", api_key, org_id)
)

prompt_config = sk.PromptTemplateConfig.from_completion_parameters(
    max_tokens=2000, temperature=0.7, top_p=0.4
)

prompt_template = sk.PromptTemplate(
    sk_prompt, kernel.prompt_template_engine, prompt_config
)

function_config = sk.SemanticFunctionConfig(prompt_config, prompt_template)
chat_function = kernel.register_semantic_function("ChatBot", "Chat", function_config)


async def chat(context_vars: sk.ContextVariables) -> bool:
    try:
        user_input = input("User:> ")
        context_vars["user_input"] = user_input
    except KeyboardInterrupt:
        print("\n\nExiting chat...")
        return False
    except EOFError:
        print("\n\nExiting chat...")
        return False

    if user_input == "exit":
        print("\n\nExiting chat...")
        return False

    answer = await kernel.run_async(chat_function, input_vars=context_vars)
    context_vars["chat_history"] += f"\nUser:> {user_input}\nChatBot:> {answer}\n"

        # Store conversation history in DynamoDB
    conversation_id = str(uuid.uuid4())
    created_time = datetime.utcnow().isoformat() + "Z"

    user_item = {
        "Id": conversation_id,
        "ParentId": "Copple",
        "CreatedTime": created_time,
        "Message": user_input,
        "Role": "User"
    }

    assistant_item = {
        "Id": conversation_id,
        "ParentId": "Copple",
        "CreatedTime": created_time,
        "Message": answer,
        "Role": "Chatbot"
    }

    # DynamoDB: Store user and assistant messages
    conversation_history_table.put_item(Item=user_item)
    conversation_history_table.put_item(Item=assistant_item)

    print(f"ChatBot:> {answer}")
    return True


async def main() -> None:
    context = sk.ContextVariables()
    context["chat_history"] = ""

    chatting = True
    while chatting:
        chatting = await chat(context)


if __name__ == "__main__":
    asyncio.run(main())