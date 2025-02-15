import streamlit as st
import cohere
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import getpass
import os
import matplotlib.pyplot as plt
import pandas as pd

class MyDecoder(json.JSONDecoder):
    def decode(self, s):
        result = super().decode(s)
        return self._decode(result)

    def _decode(self, o):
        if isinstance(o, str):            
            try:
                if '.' in o:
                    return float(o)
                return int(o)
            except ValueError:
                return o
        elif isinstance(o, dict):
            return {k: self._decode(v) for k, v in o.items()}
        elif isinstance(o, list):
            return [self._decode(v) for v in o]
        else:
            return o

load_dotenv()

responded = None

if not os.environ.get("COHERE_API_KEY"):
    os.environ["COHERE_API_KEY"] = getpass.getpass("COHERE API Key:")

co = cohere.ClientV2(api_key=os.environ.get("COHERE_API_KEY"))

st.session_state.disabled = True

@st.dialog(" ")
def vote(item):
    #st.write(f"タイトル入力")
    reason = st.text_input("タイトルを入力してください")
    if not reason == "":
        st.session_state.disabled = False
    else:
        st.session_state.disabled = True
    
    if st.button("確定", disabled=st.session_state.disabled):
        st.session_state['key'] = reason
        st.session_state['vote'] = {"item": item, "reason": reason}
        st.rerun()

def unicode_unescape(data):
    if isinstance(data, dict):
        return {key: unicode_unescape(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [unicode_unescape(item) for item in data]
    elif isinstance(data, str):
        return data.encode('utf-8').decode('unicode-escape')
    else:
        return data

# Create the tools
def search_faqs(query):
    response = requests.get("https://www.ryhintl.com/dbjson/getjson?sqlcmd=SELECT concat(q,': ',a) as `text` FROM faq")

    if response.status_code == 200:
        result = response.content.decode('utf-8') 
    
    faqs = eval(result)
    
    return faqs

def search_rev(query):
    response1 = requests.get("https://www.ryhintl.com/dbjson/getjson?sqlcmd=select * from spo_sumrevenue", verify=False)
    response_json1 = MyDecoder().decode(response1.text)
    #rev = pd.DataFrame(response_json1)
    
    return response_json1


def search_emails(query):
    # 今日の日付を取得
    today = datetime.today()

    # 一週間前の日付を計算
    one_week_ago = today - timedelta(days=7)
    
    headers = {
        'SPOAuthentication': 'Hanipman',
    }
    response = requests.get("https://www.ryhintl.com/scripts/exc2spo.exe/getjson?sqlcmd=select subject,sender_emailAddress_address as `from`,sender_emailAddress_address as `to`,receivedDateTime as `date`,webLink as `text` from O365GW.Messages where UserId = '60cdf6be-44df-4c0b-aa34-72ad4380e6c9' and receivedDateTime <= '"+str(today)+"' and receivedDateTime >= '"+str(one_week_ago)+"' order by date desc", headers=headers)

    if response.status_code == 200:
        result = response.content.decode('utf-8')
    
    emails = eval(result)
    
    return emails


def create_calendar_event(date: str, time: str, duration: int):
    title = st.session_state.vote['reason']

    @st.dialog("イベントタイトル")
    def vote(item):
        st.write(f"イベントタイトル")
        title = st.text_input("イベントタイトルを入力してください。")
        if st.button("Submit"):
            st.session_state.vote = {"title": title}
            st.rerun()

    headers = {
        'SPOAuthentication': 'Hanipman',
    }
    
    start = date+' '+time
    #start = datetime.strptime(date+' '+time+':00', '%Y/%m/%d %H:%M:%S')
    #start = st.strftime('%Y/%m/%d %H:%M:%S')
    #sdatetime = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
    #end = date+' '+time+'+'+str(duration)
    
    dt = datetime.strptime(date+' '+time+':00', '%Y/%m/%d %H:%M:%S')
    new_dt = dt + timedelta(hours=duration)
    end = new_dt.strftime('%Y-%m-%d %H:%M:%S')
    #end = datetime.strptime(str(new_dt), '%Y/%m/%d %H:%M:%S')
    
    st.write(start)
    st.write(end)
    #sqlcmd = f"https://www.ryhintl.com/scripts/exc2spo.exe/getjson?sqlcmd=insert into O365GW.Events (subject,organizer_emailAddress_address,UserId) #values('スケジュール','agent@mail.com','60cdf6be-44df-4c0b-aa34-72ad4380e6c9')"
    
    sqlcmd = f"https://www.ryhintl.com/scripts/exc2spo.exe/getjson?sqlcmd=insert into O365GW.Events (subject,,start_dateTime,end_dateTime,organizer_emailAddress_address,UserId, start_timeZone, end_timeZone) values('{title}','{start}','{end}','agent@mail.com','60cdf6be-44df-4c0b-aa34-72ad4380e6c9', 'Asia/Tokyo', 'Asia/Tokyo')"
    
    st.write(sqlcmd)
    
    '''sqlcmd = f"https://www.ryhintl.com/scripts/exc2spo.exe/getjson?sqlcmd=insert into O365GW.Events (subject,start_dateTime,end_dateTime,organizer_emailAddress_address) values('{title}','{start}','{end}','agent@mail.com') where UserId = '60cdf6be-44df-4c0b-aa34-72ad4380e6c9'"'''
    
    response = requests.get(sqlcmd, headers=headers)

    if response.status_code == 200:
        result = response.content.decode('utf-8')
        
    #events = eval(result)
    #print(result)
    
    
    global responded
    responded = f"{title}を{date} の {time} に {duration} 時間のイベントを作成しました。"
    
    return {
        "is_success": True,
        "message": f"{title}を{date} の {time} に {duration} 時間のイベントを作成しました。",
    }


functions_map = {
    "search_faqs": search_faqs,
    "search_rev": search_rev,
    "search_emails": search_emails,
    "create_calendar_event": create_calendar_event,
}


# Define the tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_faqs",
            "description": "ユーザーのクエリを指定すると、企業のよくある質問 (FAQ) リストを検索し、クエリに最も関連性の高い一致を返します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query from the user",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_rev",
            "description": "ユーザーのクエリを指定すると、売上情報 (spo_sumrevenue) リストを検索し、クエリに最も関連性の高い一致を返します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query from the user",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "ユーザーのクエリを指定すると、個人の電子メールを検索し、クエリに最も関連性の高い一致を返します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query from the user",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "指定された日時に指定された期間の新しいカレンダー イベントを作成します。新しいイベントを既存のイベントと同時に作成することはできません。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "the date on which the event starts, formatted as yyyy/mm/dd",
                    },
                    "time": {
                        "type": "string",
                        "description": "the time of the event, formatted using 24h military time formatting",
                    },
                    "duration": {
                        "type": "number",
                        "description": "the number of hours the event lasts for",
                    },
                },
                "required": ["date", "time", "duration"],
            },
        },
    },
]

# Streamlit UI
st.title("RYH CO-AGENT")

if "vote" not in st.session_state:
    #st.write("タイトル入力")
    if st.button("タイトル入力"):
        vote("タイトル")
    #if st.button("B"):
        #vote("B")
else:
    #f"You voted for {st.session_state.vote['item']} because {st.session_state.vote['reason']}"
    f"{st.session_state.vote['reason']}がタイトルとして入力されました。実行ボタンを押してください。"
    #st.toast('タイトルが設定されました。実行ボタンを押してください。')


# Input for AGENT Prompt
rev_prompt = st.text_input("プロンプトを入力してください:","北米の売上情報がありますか?もし、あればその結果を表示してください。")

# Button to get response
if st.button("確認"):
    # Create custom system message
    system_message = """## Task and Context
    あなたは、新入社員の最初の 1 週間を支援するアシスタントです。あなたは彼らの質問に答え、彼らのニーズに応えます。"""
    
    # Step 1: Get user message
    rev_message = rev_prompt

    # Add the system and user messages to the chat history
    rev_messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": rev_message},
    ]

    # Step 2: Tool planning and calling
    rev_response = co.chat(
        model="command-r-plus-08-2024", messages=rev_messages, tools=tools
    )

    if rev_response.message.tool_calls:
        print("Tool plan:")
        print(rev_response.message.tool_plan, "\n")
        print("Tool calls:")
        for tc in rev_response.message.tool_calls:
            print(
                f"Tool name: {tc.function.name} | Parameters: {tc.function.arguments}"
            )

        # Append tool calling details to the chat history
        rev_messages.append(
            {
                "role": "assistant",
                "tool_calls": rev_response.message.tool_calls,
                "tool_plan": rev_response.message.tool_plan,
            }
        )


    # Step 3: Tool execution
    for tc in rev_response.message.tool_calls:
        tool_result = functions_map[tc.function.name](
            **json.loads(tc.function.arguments)
        )
        
        crev = pd.DataFrame(tool_result)
        #st.write(crev)
        st.bar_chart(crev, x="country", y="amount")
        
        tool_content = []
        for data in tool_result:
            tool_content.append(
                {
                    "type": "document",
                    "document": {"data": json.dumps(data)},
                }
            )
            # Optional: add an "id" field in the "document" object, otherwise IDs are auto-generated
        # Append tool results to the chat history
        rev_messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_content,
            }
        )

        print("Tool results:")
        for result in tool_content:
            decoded_data = unicode_unescape(result)
            print(decoded_data)


    # Step 4: Response and citation generation
    rev_response = co.chat(
        model="command-r-plus-08-2024", messages=rev_messages, tools=tools
    )

    # Append assistant response to the chat history
    rev_messages.append(
        {"role": "assistant", "content": rev_response.message.content[0].text}
    )

    # Print final response
    print("Response:")
    print(rev_response.message.content[0].text)
    print("=" * 50)

    # Print citations (if any)
    if rev_response.message.citations:
        print("\nCITATIONS:")
        for citation in rev_response.message.citations:
            print(citation, "\n")
            
    st.write(rev_response.message.content[0].text)

    


# Input for AGENT Prompt
prompt = st.text_input("プロンプトを入力してください:","楽天からのメッセージはありますか?もし、あればその件名、送信者、URLを表示してください。")

# Button to get response
if st.button("生成"):
    # Create custom system message
    system_message = """## Task and Context
    あなたは、新入社員の最初の 1 週間を支援するアシスタントです。あなたは彼らの質問に答え、彼らのニーズに応えます。"""
    
    #messages = run_assistant(prompt)
    # Step 1: Get user message
    message = prompt

    # Add the system and user messages to the chat history
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": message},
    ]

    # Step 2: Tool planning and calling
    response = co.chat(
        model="command-r-plus-08-2024", messages=messages, tools=tools
    )

    if response.message.tool_calls:
        print("Tool plan:")
        print(response.message.tool_plan, "\n")
        print("Tool calls:")
        for tc in response.message.tool_calls:
            print(
                f"Tool name: {tc.function.name} | Parameters: {tc.function.arguments}"
            )

        # Append tool calling details to the chat history
        messages.append(
            {
                "role": "assistant",
                "tool_calls": response.message.tool_calls,
                "tool_plan": response.message.tool_plan,
            }
        )


    # Step 3: Tool execution
    for tc in response.message.tool_calls:
        tool_result = functions_map[tc.function.name](
            **json.loads(tc.function.arguments)
        )
        tool_content = []
        for data in tool_result:
            tool_content.append(
                {
                    "type": "document",
                    "document": {"data": json.dumps(data)},
                }
            )
            # Optional: add an "id" field in the "document" object, otherwise IDs are auto-generated
        # Append tool results to the chat history
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_content,
            }
        )

        print("Tool results:")
        for result in tool_content:
            decoded_data = unicode_unescape(result)
            print(decoded_data)


    # Step 4: Response and citation generation
    response = co.chat(
        model="command-r-plus-08-2024", messages=messages, tools=tools
    )

    # Append assistant response to the chat history
    messages.append(
        {"role": "assistant", "content": response.message.content[0].text}
    )

    # Print final response
    print("Response:")
    print(response.message.content[0].text)
    print("=" * 50)

    # Print citations (if any)
    if response.message.citations:
        print("\nCITATIONS:")
        for citation in response.message.citations:
            print(citation, "\n")
            
    st.write(response.message.content[0].text)

def run_assistant(query, messages=None):
    if messages is None:
        messages = []

    if "system" not in {m.get("role") for m in messages}:
        messages.append({"role": "system", "content": system_message})

    # Step 1: get user message
    print(f"Question:\n{query}")
    print("=" * 50)

    messages.append({"role": "user", "content": query})

    # Step 2: Generate tool calls (if any)
    response = co.chat(model=model, messages=messages, tools=tools)

    while response.message.tool_calls:

        print("Tool plan:")
        print(response.message.tool_plan, "\n")
        print("Tool calls:")
        for tc in response.message.tool_calls:
            print(
                f"Tool name: {tc.function.name} | Parameters: {tc.function.arguments}"
            )
        print("=" * 50)

        messages.append(
            {
                "role": "assistant",
                "tool_calls": response.message.tool_calls,
                "tool_plan": response.message.tool_plan,
            }
        )
        
        # Step 3: Get tool results
        for idx, tc in enumerate(response.message.tool_calls):
            tool_result = functions_map[tc.function.name](
                **json.loads(tc.function.arguments)
            )
            tool_content = []
            for data in tool_result:
                tool_content.append(
                    {
                        "type": "document",
                        "document": {"data": json.dumps(data)},
                    }
                )
            # Optional: add an "id" field in the "document" object, otherwise IDs are auto-generated
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_content,
                }
            )

        # Step 4: Generate response and citations
        response = co.chat(
            model=model, messages=messages, tools=tools
        )

    messages.append(
        {
            "role": "assistant",
            "content": response.message.content[0].text,
        }
    )

    # Print final response
    print("Response:")
    print(response.message.content[0].text)
    print("=" * 50)

    # Print citations (if any)
    if response.message.citations:
        print("\nCITATIONS:")
        for citation in response.message.citations:
            print(citation, "\n")

    return response.message.content[0].text

# Input for AGENT Prompt
prompt1 = st.text_input("プロンプトを入力してください:","【楽天モバイル】利用獲得ポイントのお知らせがあるか確認して、タイトルは確認するお知らせにしてカレンダーに午後12時に1時間のイベントを作成してください。")

# Button to get response
if st.button("実行"):
    with st.status("処理中...", expanded=False) as status:
        if "vote" in st.session_state:
            model = "command-r-plus-08-2024"

            system_message = """## Task and Context
            あなたは、新入社員の最初の 1 週間を支援するアシスタントです。あなたは彼らの質問に答え、彼らのニーズに応えます。"""


            messagesrun = run_assistant(
                prompt1
            )

            st.write(responded)

            status.update(
                label="✅ 完了しました！", state="complete", expanded=False
            )

        else:
            vote("タイトル")


#cdata = {
    #"pie_chart": {
        #"labels": ["United States", "Canada", "Brazil", "Argentina", "Paraguay", "United Kingdom", "Germany", "Spain", "Russia", "China", "Japan", "South Korea", "Australia", "South Africa", "Egypt"],
        #"sizes": [1001740, 1001965, 1005260, 1002790, 1003140, 1006175, 1004575, 1003680, 1002260, 1002910, 1008400, 1001325, 2006140, 1000940, 1001630]
    #}
#}

#cdata = json.load(data)

# Pie Chart
#st.subheader("Pie Chart")
#pie_chart_data = cdata['pie_chart']
#plt.pie(pie_chart_data['sizes'], labels=pie_chart_data['labels'])
#st.pyplot( plt )


response = requests.get("https://ckan.pf-sapporo.jp/api/action/datastore_search?resource_id=5678d107-d9a4-4f81-8f57-092aac11db5e&limit=100", verify=False)
response_json = MyDecoder().decode(response.text)
df = pd.json_normalize(response_json, record_path=["result", "records"])

df_pt = df[df['アレイ'].isin(['J1'])].set_index('日時')[['大通り→札幌', '札幌→大通り']]

st.write(" ")
st.write(" ")
st.write(" ")
st.write("札幌チカホ人流データ")
st.write(df_pt)
st.line_chart(df_pt)

# Footer
st.write("Powered by Streamlit")
