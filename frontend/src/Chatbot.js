import React, { useState, useEffect, useRef } from 'react';
import { Container, Form, Button } from 'react-bootstrap';
import { marked, use } from 'marked';
import './Chatbot.css'; // Ensure you have a Chatbot.css file with the styles



// Custom renderer for certain blocks
const renderer = new marked.Renderer();
renderer.code = (code, language) => {
  //console.log('rendering code:', code);
  return `<div class="chat-code-block"><code>${code}</code></div>`;
};



function Chatbot({ user, actor, thread, actorList, onActorChange, onThreadListChange }) {

  const [prompt, setPrompt] = useState('');
  const [chat, setChat] = useState([]);
  const chatEndRef = useRef(null);


  const updateChat = (action) => {
    setChat(currentChat => {
      switch (action.type) {
        case 'set':
          return action.messages;
        case 'add':
          return [...currentChat, ...action.messages];
        case 'update':
          const clonedChat = [...currentChat];
          clonedChat[clonedChat.length - 1] = {...clonedChat[clonedChat.length - 1]}
          clonedChat[clonedChat.length - 1].value += action.text;
          return clonedChat;
        default:
          return currentChat;
      }
    });
  }

  // update the actor with the current info from the server
  const handleActorSelection = async (actorName) => {
    onActorChange(actorName);
  };   

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(scrollToBottom, [chat]);

  useEffect(() => {
    if (thread !== null) {
      //console.log(`Chat: thread response: ${JSON.stringify(thread)}`)
      if (thread.messages !== null) {
        const messages = JSON.parse(thread.messages);
        //console.log(`Chat: thread messages: ${JSON.stringify(messages)}`)
        updateChat({ type: 'set', messages: messages });
      } else {
        updateChat({ type: 'set', messages: [] });
      }
    }
  }, [thread]);  

  const markdownText = (text) => {
    return marked(text, { sanitize: true, renderer: renderer });
  }

  const renderMessage = (chatMessage) => {
    const msgValue = chatMessage.value;
    const msgType = chatMessage.type;
    //console.log('rendering message:', chatMessage);
    if (typeof msgValue === 'string' || msgValue instanceof String) {
        if (msgValue.startsWith('data:image/png;base64')) {
            return (
                <img src={msgValue} alt="image response" />
            );
        } else {
            if (chatMessage.role === 'user') {
              return (
                <div className="message user-message">{msgValue}</div>
              );
            } else {
              return (
                <div className="message bot-message" dangerouslySetInnerHTML={{ __html: markdownText(msgValue) }} />
              );
            }
        }
    } else {
        console.log('ERROR: received non string:', chatMessage); 
    }
  };

  const renderChat = (chat) => {
    if (chat === null || chat.length === 0) return ( <div></div> );
    return chat.map((chatMessage, index) => (
      <div key={index} className={`message ${chatMessage.role === 'user' ? 'user-message' : 'bot-message'}`}>
        {renderMessage(chatMessage)}
      </div>
    ));
  }


  const sendPrompt = async (e) => {
    console.log(`sending prompt: ${prompt}`);

    e.preventDefault();
    if (!prompt.trim()) return; // Prevent sending empty messages
    updateChat({ type: 'add', messages: [{ 'value': prompt, 'role': 'user', type: 'text' } ,
                                         { 'value': '', 'role': 'assistant', type: 'text' }] });
    setPrompt(''); //clear the buffer
    

    var postData = { actor: actor.actor_name, input: prompt, user: user, buffer_size: 10 };
    if (thread !== null) {
      postData['thread'] = thread.thread_id;
    }

    try {
      const decoder = new TextDecoder();
      const response = await fetch('http://127.0.0.1:8000/api/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',  
        },
        body: JSON.stringify(postData),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const reader = response.body.getReader();
      let streamLength = 0;
      let imageBuffer = '';
      const readStream = () => {
        reader.read().then(({ done, value }) => {
          
          if (done) {
            console.log('Stream complete: ', streamLength, 'bytes');
            return;
          }
          
          streamLength += value.byteLength;
          const msgString = decoder.decode(value, { stream: true })
          if (msgString.startsWith('data:image/png;base64')) {
            imageBuffer += msgString;
          } else {
            //end of the image
            if (imageBuffer.length > 0) {
              if (msgString.includes('|')) {
                const [beforePipe, afterPipe] = msgString.split('|');
                if (beforePipe.length > 0) {
                  imageBuffer += beforePipe;
                }
                if (afterPipe.length > 0) {
                  afterPipe = '';
                }
                updateChat({ type: 'add', messages: [
                              { 'value': imageBuffer, 'role': 'assistant', type: 'image' },
                              { 'value': '', 'role': 'assistant', type: 'text' }
                          ] });
                imageBuffer = '';
              } else {
                imageBuffer += msgString;
              }
            } else {
              updateChat({ type: 'update', text: msgString });
            }
          }

          readStream();
        }).catch(error => {
          console.error('Error reading stream:', error);
        });
      };
      readStream();

    } catch (error) {
      console.error('Stream: error:', error);
    }

    onThreadListChange();
  };


  if (actor == null) {
    return ( <div className="chatbot-container"></div> );
  } else {
    return (
        <div className="chatbot-container">

          <div className="chat-window">
            {renderChat(chat)}
            <div ref={chatEndRef} />
          </div>
          <div className='chat-header'>
              <Form.Select className="chat-title" defaultValue={actor.actor_name}
                onChange={(e) => handleActorSelection(e.target.value, false)}> 
              {actorList.map((actorItem, index) => (
                    <option 
                      value={actorItem.actor_name} 
                      key={actorItem.actor_name}>
                        {actorItem.actor_name}
                    </option>
              ))}
              </Form.Select>
            <div className="chat-description">{actor.description}</div>
          </div>
          <Form onSubmit={sendPrompt} className="message-form">
            <div className="chat-input">
                <Form.Control
                    type="text"
                    placeholder="Type your prompt here..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    autoFocus
                    className="dark-input"
                />
                <div className="input-group-append">
                    <Button variant="outline-secondary" type="submit" className="input-arrow">
                        ➤
                    </Button>
                </div>
            </div>
          </Form>

        </div>
    );
  }

}

export default Chatbot;


