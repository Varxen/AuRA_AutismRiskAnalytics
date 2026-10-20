from nicegui import ui

from chatbot_v0_7_3 import (
    QUESTIONS,
    process_text,
    FEATURES
)


@ui.page('/')
def index():

    

    language = 'en'
    current_question = 0

    cumulative_vector = [0] * len(FEATURES)

    messages = [('bot', QUESTIONS[language][0]["question"])]

    # --------------------------------------------------
    # Header
    # --------------------------------------------------

    drawer = ui.left_drawer(value=True).classes('bg-gray-100').props('width=300')

    def toggle_drawer():
        drawer.toggle()
        update_input_width()

    with ui.header().classes('items-center'):

        ui.button(
            icon='menu',
            on_click=toggle_drawer
        ).props('flat round dense')

        ui.label('AuRA').classes(
            'text-xl font-bold ml-2'
        )

    # --------------------------------------------------
    # Sidebar
    # --------------------------------------------------       

    with drawer:
        ui.label('AuRA').classes('text-2xl font-bold p-4')

        ui.button('+ New Chat').classes('w-full')

        ui.separator()

        ui.label('Chats').classes('text-sm text-gray-500 p-3')

        ui.button('Assessment No. X', icon='chat') \
            .props('flat').classes('w-full justify-start')

        ui.space()

        ui.separator()

        ui.button('Settings', icon='settings') \
            .props('flat') \
            .classes('w-full justify-start')

    # --------------------------------------------------
    # Chat display
    # --------------------------------------------------

    @ui.refreshable
    def chat_messages():
        for sender, text in messages:
            with ui.row().classes(
                'w-full ' + (
                    'justify-end' if sender == 'user' 
                    else 'justify-start'
                )
            ):
                ui.chat_message(
                    text=text,
                    sent=(sender == 'user')
                ).classes('max-w-[80%] mb-3 text-base')

    # --------------------------------------------------
    # Process user response
    # --------------------------------------------------

    def send():

        nonlocal current_question
        nonlocal cumulative_vector

        user_response = text.value.strip()

        if not user_response:
            return

        # Display user's message
        messages.append(
            ('user', user_response)
        )

        text.value = ''

        # Get current question
        question = QUESTIONS[language][current_question]

        # Run NLP
        msg, tokens, detected, vector_data = process_text(
            user_response,
            language,
            question["indicator"]
        )

        question_vector = vector_data[0]

        # Update cumulative vector
        cumulative_vector = [
            max(old, new)
            for old, new in zip(
                cumulative_vector,
                question_vector
            )
        ]

        # Debug
        print("Detected:", detected)
        print("Question vector:", question_vector)
        print("Cumulative:", cumulative_vector)

        # Move to next question
        current_question += 1

        # Display next question
        if current_question < len(QUESTIONS[language]):

            next_question = QUESTIONS[language][current_question]

            messages.append(
                ('bot', next_question["question"])
            )

        else:

            messages.append(
                (
                    'bot',
                    'Thank you. The questionnaire is complete.'
                )
            )

            print("Final ML input vector:")
            print(cumulative_vector)

        chat_messages.refresh()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    with ui.column().classes('w-full h-full px-6 py-6'):

        ui.label('AuRA').classes(
            'text-2xl font-bold'
        )

        ui.label(
            'Autism Risk Assessment Assistant'
        ).classes(
            'text-gray-500 mb-4'
        )

        chat_messages()

    # --------------------------------------------------
    # Input
    # --------------------------------------------------

    ui.add_css('''
        .chat-footer {
            margin-left: 300px;
            width: calc(100% - 300px);
            transition: margin-left 0.3s, width 0.3s;
        }
    ''')

    input_container = ui.row().classes(
        'fixed bottom-0 right-0 items-center bg-white px-6 py-3'
    )

    def update_input_width():
        if drawer.value:
            input_container.style(
                'left: 300px; right: 0; width: calc(100% - 300px);'
            )
        else:
            input_container.style(
                'left: 0;right: 0; width: 100%;'
            )

    update_input_width()

    with input_container:

        text = ui.input(
            placeholder='Type your response...'
        ).props(
            'rounded outlined'
        ).classes(
            'flex-grow'
        ).on(
            'keydown.enter',
            send
        )

        ui.button(
            'Send',
            on_click=send
        )


# --------------------------------------------------
# Start
# --------------------------------------------------

ui.run()