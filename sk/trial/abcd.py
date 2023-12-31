# Copyright (c) Microsoft. All rights reserved.

import asyncio

import semantic_kernel as sk
import semantic_kernel.connectors.ai.open_ai as sk_oai

sk_prompt = """
ChatBot can have a conversation with you about any topic.
It can give explicit instructions or say 'I don't know'
when it doesn't know the answer.
{{$chat_history}}
User:> {{$user_input}}
ChatBot:>
"""

summarize_prompt """
You are a schedule summary. Displays a summary of your schedule in the latest order based on today's date.
"""

extract_prompt = """
You need to know how to distinguish parameters based on the values you enter. First, the default parameter is "title", "startDatime", "endDatime", "location", "content", "image" and "isCompleted".
title should contain something symbolic or representative of the value entered by the user. 
startDatetime is An event, schedule, or schedule begins. Must specify "year-month-day-hour-minute" with no words. only datetime.
endDatime is when an event, schedule, or schedule ends. But when there is no endDatetime specified, add one hour from startDatetime. Must specify "year-month-day-hour-minutes" with no words. only datetime.
location means meeting someone or a place. 
I hope the content includes anything other than behavioral and planning. 
image value is always null.
isCompleted value begins with false unless users specify when they say or mention it is done or complete. They they say or mention it is complete, change the value from false to true.
When answering, ignore special characters, symbols and blank spaces. Just answer title, startDatetime, endDatetime, location,content, image, and isCompleted.

Second step is choose only one that fits well with the context of the conversation from users.

Here is 6 definition of words. 

QueryByTime: The user wants to find information about user's plan, and a time range is given.

QueryByQuery: The user wants to find information about user's plan, but no time range is provided.

CreatePlan: The user wants to create a plan. 

RecommandPlan: the user asks for recommendations for plan

UpdatePlan: The user wants to modify an user's plan.

DeletePlan: The user wants to delete an user's plan.

{{$chat_history}}
User:> {{$user_input}}
"""

crud_prompt = """  
QueryByTime: The user wants to find information about user's plan, and a time range is given.

QueryByQuery: The user wants to find information about user's plan, but no time range is provided.

CreatePlan: The user wants to create a plan. 

RecommandPlan: the user asks for recommendations for plan

UpdatePlan: The user wants to modify an user's plan.

DeletePlan: The user wants to delete an user's plan.

You have six definitions , and you need to choose only one that fits well with the context of the conversation

Through the user's conversation, understanding context-appropriate words, and then extracting active content in the next sentence, 
if it's QueryByTime, ask ""content"을/를 조회하시겠습니까?"
If it's QueryByQuery, ask ""content + time"을 조회하시겠습니까?"
If it's CreatePlan, ask ""content"을/를 추가하시겠습니까?"
If it's RecommandPlan, ask ""content"을/를 추천해드릴까요?"
If it's UpdatePlan, ask ""content"을 변경 또는 수정하시겠습니까?"
If it's DeletePlan, ask ""content"을 삭제하시겠습니까?"
"""


kernel = sk.Kernel()

api_key, org_id = sk.openai_settings_from_dot_env()
kernel.add_chat_service(
    "chat-gpt", sk_oai.OpenAIChatCompletion("gpt-3.5-turbo", api_key, org_id)
)

prompt_config = sk.PromptTemplateConfig.from_completion_parameters(
    max_tokens=2000, temperature=0.7, top_p=0.4
)

prompt_template = sk.PromptTemplate(
    sk_prompt, kernel.prompt_template_engine, prompt_config
)

extract_template = sk.PromptTemplate(
    extract_prompt, kernel.prompt_template_engine, prompt_config
)

crud_template = sk.PromptTemplate(
    crud_prompt, kernel.prompt_template_engine, prompt_config
)

function_config = sk.SemanticFunctionConfig(prompt_config, prompt_template)
chat_function = kernel.register_semantic_function("ChatBot", "Chat", function_config)

extract_function_config = sk.SemanticFunctionConfig(prompt_config, extract_template)
extract_function = kernel.register_semantic_function("EXTRACT", "Extract", extract_function_config)

crud_function_config = sk.SemanticFunctionConfig(prompt_config, crud_template)
crud_function = kernel.register_semantic_function("CRUD", "Crud", crud_function_config)

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

    # Run extract_function
    extracted_response = await kernel.run_async(extract_function, input_vars=context_vars)

    # Check if extract_function provided a valid response
    if not extracted_response or "error" in extracted_response:
        # If not, run crud_function
        answer = await kernel.run_async(crud_function, input_vars=context_vars)
    else:
        # If it is a CRUD action, execute the crud_function
        if "QueryByTime"  or "QueryByQuery"  or "CreatePlan"  or "RecommandPlan"  or "UpdatePlan" or "DeletePlan":
            crud_response = await kernel.run_async(crud_function, input_vars=context_vars)
            answer = crud_response
        else:
            # If not, run chat_function
            answer = await kernel.run_async(chat_function, input_vars=context_vars)

    context_vars["chat_history"] += f"\nUser:> {user_input}\nChatBot:> {answer}\n"
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
