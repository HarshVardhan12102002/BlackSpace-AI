import React, { useContext, useState, useEffect } from "react";
import { assets } from "../../assets/assets";
import "./Main.css";
import { Context } from "../../context/Context";

const Main = () => {
  const {
    onSent,
    recentPrompt,
    showResult,
    loading,
    resultData,
    setInput,
    input,
  } = useContext(Context);

  const [isListening, setIsListening] = useState(false);

  useEffect(() => {
    let recognition;

    const handleResult = (event) => {
      const current = event.resultIndex;
      const transcript = event.results[current][0].transcript;
      setInput(transcript);
    };

    const handleError = (error) => {
      console.error('Speech recognition error:', error);
      setIsListening(false);
    };

    if (isListening) {
      recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.onresult = handleResult;
      recognition.onerror = handleError;
      recognition.start();
    }

    return () => {
      if (recognition) {
        recognition.stop();
      }
    };

  }, [isListening]);

  const toggleListening = () => {
    setIsListening((prevIsListening) => !prevIsListening);
  };

  return (
    <div className="main">
      <div className="nav">ƒˇ
        <p>blackspace.ai</p>
        <img src={assets.user_icon} alt="" />
      </div>
      <div className="main-container">
        {!showResult ? (
          <>
            <div className="greet">
              <p>
                <span>Hello 👋.</span>
              </p>
              <p>How can I help you today?</p>
            </div>
            <div className="cards">
              <div className="card">
                <p>Ask any doubts or questions you have about 100xEngineers & our courses.</p>
                <img src={assets.compass_icon} alt="" />
              </div>
              <div className="card">
                <p>Upload your resume and get free consulation from our AI councellor.</p>
                <img src={assets.bulb_icon} alt="" />
              </div>
            </div>
          </>
        ) : (
          <div className="result">
            <div className="result-title">
              <img src={assets.user_icon} alt="" />
              <p>{recentPrompt}</p>
            </div>
            <div className="result-data">
              <img src={assets.gemini_icon} alt="" />
              {loading ? (
                <div className="loader">
                  <hr />
                  <hr />
                  <hr />
                </div>
              ) : (
                <p dangerouslySetInnerHTML={{ __html: resultData }}></p>
              )}
            </div>
          </div>
        )}

        <div className="main-bottom">
          <div className="search-box">
            <input
              onChange={(e) => setInput(e.target.value)}
              value={input}
              type="text"
              placeholder="Ask your questions here..."
              onKeyDown={(e) => e.key === "Enter" && onSent()}
            />
            <div>
              <img src={assets.gallery_icon} alt="" />

              <div onClick={toggleListening}>
                <img  src={assets.mic_icon} alt="" />
              </div>

              {input ? (
                <img onClick={() => onSent()} src={assets.send_icon} alt="" />
              ) : null}
            </div>
          </div>
          <p className="bottom-info">
            blackspace.ai may display inaccurate info, including about people, so
            double-check its responses.Your privacy and blackspace.ai
          </p>
        </div>
      </div>
    </div>
  );
};

export default Main;
