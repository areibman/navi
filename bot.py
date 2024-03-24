from pathlib import Path
from autogen.coding import LocalCommandLineCodeExecutor
import autogen
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json, GroupChatManager
# Load LLM inference endpoints from an env variable or a file
# See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
# and OAI_CONFIG_LIST_sample

config_list = [
    {
        "model": "gpt-4-turbo-preview",
        "api_key": ""
    },
]


def get_human_input(prompt: str) -> str:
    return "Looks good to me"


# user_proxy.get_human_input = get_human_input


def process_link_with_agent(message: str) -> str:

    llm_config = {
        "timeout": 600,
        "cache_seed": None,
        "config_list": config_list,
        "temperature": 0,
    }

    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        llm_config=llm_config,
    )

    # assistant.update_system_message(assistant.system_message + "\nYou can get user's feedback using get_user_feedback function.")

    # create a UserProxyAgent instance named "user_proxy"
    # Code executor. Does not say anything unless there is no code to run.
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="TERMINATE",
        max_consecutive_auto_reply=10,
        is_termination_msg=lambda x: x.get(
            "content", "").rstrip().endswith("TERMINATE"),
        # code_execution_config={"executor": code_executor},
        code_execution_config={
            "work_dir": ".web",
            "use_docker": False,
        },
        # system_message="""Reply TERMINATE if the task has been solved at full satisfaction.
        # Otherwise, reply CONTINUE, or the reason why the task is not solved yet.""",
    )

    def get_human_input(prompt: str) -> str:
        return "TERMINATE"

    user_proxy.get_human_input = get_human_input

    print(message)
    result = user_proxy.initiate_chat(
        assistant,
        message=message,
        summary_method="reflection_with_llm",
        summary_args={
            "summary_prompt": "Return the following fields: Company name\nWebsite\nDescription\nNotes"
        }
    )
    print('*'*100)
    print(result)
    return "Result:" + result.summary


# def async main():
#   while True:
#     await message = listen_to_messages()

#     user_proxy = ...
#     assistant = ...
#     # Other stuff with agent init, functions, etc.


#     web_data_results = user_proxy.a_initiate_chat(message)

#     if "false" in web_data_results:
#       continue

#     query_insert_results = user_proxy.a_initaite_chat(web_data_results)

#     requests.post(f'slack.com/....{query_insert_results}')
