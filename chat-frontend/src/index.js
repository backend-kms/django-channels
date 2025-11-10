import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/service_worker.js')
            .then(function(registration) {
                console.log('Service Worker 등록 성공:', registration.scope);
            }, function(err) {
                console.log('Service Worker 등록 실패:', err);
            });
    });
}

if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(function(permission) {
        if (permission === 'granted') {
            console.log('알림 권한 허용됨!');
        } else if (permission === 'denied') {
            console.log('알림 권한 거부됨!');
        } else {
            console.log('알림 권한 요청이 무시됨!');
        }
    });
}

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
