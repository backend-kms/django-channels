import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import './App.css';

// API 설정
const API_BASE_URL = 'http://localhost:8000/chat';
axios.defaults.baseURL = API_BASE_URL;
axios.defaults.withCredentials = false;

// 메시지 반응 컴포넌트
const MessageReactions = ({ messageId, currentUser, reactions: initialReactions }) => {
  const [reactions, setReactions] = useState({
    like: 0,
    good: 0,
    check: 0,
    ...initialReactions
  });
  const [userReaction, setUserReaction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // 반응 이모지 매핑
  const reactionEmojis = {
    like: '❤️',
    good: '👍',
    check: '✅'
  };

  useEffect(() => {
    if (initialReactions) {
      setReactions(prev => ({
        like: 0,
        good: 0,
        check: 0,
        ...initialReactions
      }));
    }
  }, [initialReactions]);

  // 반응 데이터 로드
  const loadReactions = useCallback(async () => {
    try {
      const response = await axios.get(`/api/messages/${messageId}/reactions/`);
      if (response.data) {
        setReactions(response.data.reaction_counts);
        setUserReaction(response.data.user_reaction);
      }
    } catch (error) {
      console.error('반응 로드 실패:', error);
    }
  }, [messageId]);

  // 반응 토글
  const handleReactionClick = async (reactionType) => {
    if (isLoading) return;

    setIsLoading(true);

    try {
      const response = await axios.post(`/api/messages/${messageId}/reaction/`, {
        reaction_type: reactionType
      });

      console.log('1. 반응 API 응답:', response.data);

      if (response.data.success) {
        const reactionCounts = response.data.reaction_counts || {};
        
        // 서버 응답에서 user_reaction 계산
        let calculatedUserReaction = null;
        if (response.data.action === 'added') {
          calculatedUserReaction = response.data.reaction_type;
        } else if (response.data.action === 'removed') {
          calculatedUserReaction = null;
        } else if (response.data.action === 'updated') {
          calculatedUserReaction = response.data.reaction_type;
        }
        
        setReactions(reactionCounts);
        setUserReaction(calculatedUserReaction);
        
        console.log('2. 반응 상태 업데이트 완료:', {
          action: response.data.action,
          userReaction: calculatedUserReaction
        });
      }
    } catch (error) {
      console.error('반응 처리 실패:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 컴포넌트 마운트 시 반응 데이터 로드
  useEffect(() => {
    loadReactions();
  }, [loadReactions]);

  return (
    <div className="message-reactions" data-message-id={messageId}>
      <div className="reaction-buttons">
        {Object.keys(reactionEmojis).map(reactionType => (
          <button
            key={reactionType}
            className={`reaction-btn ${userReaction === reactionType ? 'active' : ''}`}
            onClick={() => handleReactionClick(reactionType)}
            disabled={isLoading}
            title={`${reactionEmojis[reactionType]} ${reactionType}`}
          >
            <span className="reaction-emoji">
              {reactionEmojis[reactionType]}
            </span>
            {reactions[reactionType] > 0 && (
              <span className="reaction-count">
                {reactions[reactionType]}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};

function App() {
  // 상태 정의
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [rooms, setRooms] = useState([]);
  const [myRooms, setMyRooms] = useState([]);
  const [stats, setStats] = useState({});
  const [currentRoom, setCurrentRoom] = useState('');
  const [currentRoomInfo, setCurrentRoomInfo] = useState(null);
  const [roomName, setRoomName] = useState('');
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [socket, setSocket] = useState(null);
  const globalSocketRef = useRef(null); // 🔥 useRef로 변경
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [connected, setConnected] = useState(false);
  const messagesEndRef = useRef(null);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [roomForm, setRoomForm] = useState({ name: '', description: '', max_members: 100 });

  // JWT 토큰 관리
  const setAuthToken = useCallback((token) => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('access_token', token);
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  }, []);

  // 🔥 글로벌 WebSocket 연결 함수
  const connectGlobalSocket = useCallback((user) => {
    // 이미 연결되어 있으면 종료
    if (globalSocketRef.current && globalSocketRef.current.readyState === WebSocket.OPEN) {
      return;
    }
    
    // 기존 연결이 있으면 정리
    if (globalSocketRef.current) {
      globalSocketRef.current.close();
    }

    const ws = new WebSocket(`ws://localhost:8000/ws/global/${user.id}/`);
    
    ws.onopen = () => {
      console.log('🌐 글로벌 WebSocket 연결됨');
      globalSocketRef.current = ws;
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'unread_count_update') {
        // 특정 방의 안읽은 메시지 수 업데이트
        setMyRooms(prevRooms => 
          prevRooms.map(room => 
            room.name === data.room_name 
              ? { ...room, unread_count: data.unread_count }
              : room
          )
        );
      } else if (data.type === 'all_unread_counts') {
        // 모든 방의 안읽은 메시지 수 일괄 업데이트
        setMyRooms(prevRooms => 
          prevRooms.map(room => ({
            ...room,
            unread_count: data.unread_counts[room.name] || 0
          }))
        );
      }
    };
    
    ws.onclose = () => {
      console.log('🌐 글로벌 WebSocket 연결 해제됨');
      globalSocketRef.current = null;
    };
    
    ws.onerror = (error) => {
      console.error('🌐 글로벌 WebSocket 오류:', error);
    };
  }, []); // 🔥 의존성 배열을 빈 배열로 변경

  // 🔥 글로벌 WebSocket 해제 함수
  const disconnectGlobalSocket = useCallback(() => {
    if (globalSocketRef.current) {
      globalSocketRef.current.close();
      globalSocketRef.current = null;
    }
  }, []);

  // 데이터 로드 함수들
  const fetchRooms = useCallback(async () => {
    try {
      const response = await axios.get('/api/rooms/');
      if (response.data.results) {
        setRooms(response.data.results);
      }
    } catch (error) {
      console.error('방 목록 로드 실패:', error);
    }
  }, []);

  const fetchMyRooms = useCallback(async () => {
    if (!isAuthenticated) {
      setMyRooms([]);
      return;
    }
    
    try {
      const response = await axios.get('/api/my-rooms/');
      console.log('내 방 데이터:', response.data); // 🔍 데이터 구조 확인
      setMyRooms(response.data || []);
    } catch (error) {
      console.error('내 방 목록 로드 실패:', error);
      setMyRooms([]);
    }
  }, [isAuthenticated]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get('/api/stats/');
      if (response.data.success) {
        setStats(response.data.stats);
      }
    } catch (error) {
      console.error('통계 로드 실패:', error);
    }
  }, []);

  const fetchCurrentRoomInfo = useCallback(async (roomName) => {
    if (!roomName || !isAuthenticated) return;
    
    try {
      const response = await axios.get(`/api/rooms/${roomName}/info/`);
      if (response.data.success) {
        setCurrentRoomInfo(response.data.room);
      }
    } catch (error) {
      console.error('현재 방 정보 로드 실패:', error);
    }
  }, [isAuthenticated]);

  const markAsRead = useCallback(async (roomName) => {
    if (!roomName || !isAuthenticated) return;
    
    try {
      await axios.post(`/api/rooms/${roomName}/mark-read/`);
      
      // 🔥 읽음 처리 후 myRooms의 안읽은 수 리셋
      setMyRooms(prevRooms => 
        prevRooms.map(room => 
          room.name === roomName 
            ? { ...room, unread_count: 0 }
            : room
        )
      );
    } catch (error) {
      console.error('읽음 처리 실패:', error);
    }
  }, [isAuthenticated]);

  // WebSocket 메시지 핸들러들
  const handleMessagesReadCountUpdate = useCallback((updatedMessages, readerUsername) => {
    setMessages(prevMessages => {
      return prevMessages.map(msg => {
        const updatedMsg = updatedMessages.find(um => um.id === msg.message_id);
        if (updatedMsg) {
          return {
            ...msg,
            unreadCount: updatedMsg.unread_count,
            isReadByAll: updatedMsg.is_read_by_all
          };
        }
        return msg;
      });
    });
  }, []);

  const handleReactionUpdate = useCallback((data) => {
    console.log('3. WebSocket 반응 업데이트:', data);
    
    setMessages(prevMessages => {
      return prevMessages.map(msg => {
        if (msg.message_id === data.message_id) {
          return {
            ...msg,
            reactions: data.reaction_counts,
            lastReactionUpdate: Date.now()
          };
        }
        return msg;
      });
    });
  }, []);

  const handleChatMessage = (data) => {
    const newMessage = {
      id: data.message_id || Date.now() + Math.random(),
      message_id: data.message_id,
      text: data.message,
      author: data.username,
      time: data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
      isSystem: false,
      unreadCount: data.unread_count || 0,
      isReadByAll: data.is_read_by_all || false,
      userId: data.user_id,
      reactions: {}
    };
    
    setMessages(prev => [...prev, newMessage]);
    setTimeout(() => markAsRead(currentRoom), 100);

    // 🔥 내가 보낸 메시지가 아니면 안읽은 수 업데이트
    if (data.username !== user?.username) {
      setMyRooms(prevRooms => 
        prevRooms.map(room => {
          if (room.name === currentRoom) {
            return {
              ...room,
              last_message: data.message,
              last_message_time: new Date().toISOString()
            };
          } else {
            return room;
          }
        })
      );
    }
  };

  const handleSystemMessage = (data, roomName) => {
    const systemMessage = {
      id: Date.now() + Math.random(),
      text: data.message,
      author: data.username,
      time: new Date().toLocaleTimeString(),
      isSystem: true,
      unreadCount: 0,
      isReadByAll: true,
      userId: null,
      reactions: {}
    };
    
    setMessages(prev => [...prev, systemMessage]);
    
    if (data.message.includes('입장') || data.message.includes('퇴장')) {
      setTimeout(() => fetchCurrentRoomInfo(roomName), 500);
    }
  };

  // 사용자 액션 핸들러들
  const handleLogin = async () => {
    try {
      if (!loginForm.username.trim() || !loginForm.password.trim()) {
        alert('아이디와 비밀번호를 입력해주세요.');
        return;
      }

      console.log('1. 로그인 시도:', loginForm.username);
      const response = await axios.post('/api/auth/login/', loginForm);
      
      if (response.data.success) {
        const { access_token, refresh_token, user, message } = response.data;
        
        setAuthToken(access_token);
        localStorage.setItem('refresh_token', refresh_token);
        localStorage.setItem('user', JSON.stringify(user));
        
        setUser(user);
        setIsAuthenticated(true);
        setLoginForm({ username: '', password: '' });
        
        console.log('2. 로그인 성공:', user.username);
        alert(message);
        
        // 🔥 글로벌 WebSocket 연결
        connectGlobalSocket(user);
        
        // 데이터 새로고침
        fetchRooms();
        fetchMyRooms();
        fetchStats();
      }
    } catch (error) {
      console.error('로그인 실패:', error);
      const errorMessage = error.response?.data?.error || '로그인에 실패했습니다.';
      alert(errorMessage);
    }
  };

  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await axios.post('/api/auth/logout/', { refresh_token: refreshToken });
      }
    } catch (error) {
      console.error('로그아웃 API 오류:', error);
    } finally {
      if (socket) {
        socket.close();
      }
      
      // 🔥 글로벌 WebSocket 해제
      disconnectGlobalSocket();
      
      setAuthToken(null);
      setUser(null);
      setIsAuthenticated(false);
      setCurrentRoom('');
      setCurrentRoomInfo(null);
      setMessages([]);
      setConnected(false);
      setSocket(null);
      setMyRooms([]);
      
      console.log('로그아웃 완료');
      
      fetchRooms();
      fetchStats();
    }
  };

  const handleCreateRoom = async () => {
    try {
      if (!isAuthenticated) {
        alert('로그인이 필요합니다.');
        return;
      }

      if (!roomForm.name.trim()) {
        alert('방 이름을 입력해주세요.');
        return;
      }

      console.log('1. 방 생성 시도:', roomForm.name);
      const response = await axios.post('/api/rooms/create/', roomForm);
      
      if (response.data.success) {
        console.log('2. 방 생성 성공');
        alert(response.data.message);
        setShowCreateRoom(false);
        setRoomForm({ name: '', description: '', max_members: 100 });
        fetchRooms();
        fetchMyRooms();
      }
    } catch (error) {
      console.error('방 생성 실패:', error);
      const errorMessage = error.response?.data?.error || '방 생성에 실패했습니다.';
      alert(errorMessage);
    }
  };

  const handleJoinRoom = async (targetRoomName) => {
    try {
      if (!isAuthenticated) {
        alert('로그인이 필요합니다.');
        return;
      }

      console.log('1. 방 입장 시도:', targetRoomName);

      // 방 입장 API 호출
      const joinResponse = await axios.post(`/api/rooms/${targetRoomName}/join/`);
      
      if (joinResponse.data.success) {
        console.log('2. 서버 입장 성공');
        const isFirstJoin = joinResponse.data.is_first;
        
        // 채팅 메시지 히스토리 로드
        const messagesResponse = await axios.get(`/api/rooms/${targetRoomName}/messages/`);
        if (messagesResponse.data) {
          const loadedMessages = messagesResponse.data.map(msg => ({
            id: msg.id,
            message_id: msg.id,
            text: msg.content || msg.message,
            author: msg.username || 'Anonymous',
            time: new Date(msg.created_at).toLocaleTimeString(),
            isSystem: msg.message_type === 'system',
            unreadCount: msg.unread_count || 0,
            isReadByAll: msg.is_read_by_all || false,
            userId: msg.user_id,
            reactions: {}
          }));
          setMessages(loadedMessages);

          setTimeout(() => markAsRead(targetRoomName), 300);
        }

        // 🔥 방 입장 성공 시 해당 방의 안읽은 메시지 수 리셋
        setMyRooms(prevRooms => 
          prevRooms.map(room => 
            room.name === targetRoomName 
              ? { ...room, unread_count: 0 }
              : room
          )
        );

        setCurrentRoom(targetRoomName);
        setCurrentRoomInfo(joinResponse.data.room);
        
        // WebSocket 연결
        const ws = new WebSocket(`ws://localhost:8000/ws/chat/${targetRoomName}/`);
        
        ws.onopen = () => {
          console.log('3. WebSocket 연결됨');
          setSocket(ws);
          setConnected(true);

          if (isFirstJoin) {
            ws.send(JSON.stringify({
              type: 'user_join',
              username: user?.username,
            }));
            console.log('4. 첫 입장 - 입장 메시지 전송');
          }
          
          // 🔥 글로벌 WebSocket으로 안읽은 수 새로고침 요청
          if (globalSocketRef.current && globalSocketRef.current.readyState === WebSocket.OPEN) {
            globalSocketRef.current.send(JSON.stringify({
              type: 'refresh_unread_counts'
            }));
          }
        };
        
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          
          if (data.type === 'messages_read_count_update') {
            handleMessagesReadCountUpdate(data.updated_messages, data.reader_username);
          } else if (data.type === 'chat') {
            handleChatMessage(data);
          } else if (data.type === 'system') {
            handleSystemMessage(data, targetRoomName);
          } else if (data.type === 'reaction_update') {
            handleReactionUpdate(data);
          }
        };
        
        ws.onclose = () => {
          console.log('WebSocket 연결 해제됨');
          setSocket(null);
          setConnected(false);
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket 오류:', error);
        };

        fetchMyRooms();
        console.log('5. 방 입장 완료');
      }
    } catch (error) {
      console.error('방 입장 실패:', error);
      if (error.response?.status === 404) {
        alert('존재하지 않는 채팅방입니다.');
      } else if (error.response?.status === 400) {
        const errorMessage = error.response?.data?.error || '방이 가득 찼습니다.';
        alert(errorMessage);
      } else {
        const errorMessage = error.response?.data?.error || error.response?.data?.detail || '방 입장에 실패했습니다.';
        alert(errorMessage);
      }
    }
  };

  const handleSendMessage = () => {
    if (socket && message.trim() && connected) {
      socket.send(JSON.stringify({
        type: 'text',
        message: message.trim(),
        username: user?.username
      }));
      setMessage('');
      setTimeout(() => markAsRead(currentRoom), 100);
    } else if (!connected) {
      alert('채팅방에 연결되지 않았습니다.');
    }
  };

  const handleLeaveRoom = async () => {
    if (!currentRoom) return;

    if (!window.confirm(`'${currentRoom}' 방에서 나가시겠습니까?`)) {
      return;
    }

    const leavingRoomName = currentRoom;

    try {
      if (socket && connected) {
        socket.send(JSON.stringify({
          type: 'user_leave',
          username: user?.username,
        }));
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      await axios.post(`/api/rooms/${leavingRoomName}/leave/`);
      fetchMyRooms();
    } catch (error) {
      console.error('서버 방 퇴장 실패:', error);
    } finally {
      if (socket) {
        socket.close();
      }
      
      setCurrentRoom('');
      setCurrentRoomInfo(null);
      setMessages([]);
      setMessage('');
      setConnected(false);
      setSocket(null);
    }
  };

  const handleLeaveMyRoom = async (roomName) => {
    if (!window.confirm(`'${roomName}' 방에서 나가시겠습니까?`)) {
      return;
    }
    
    try {
      if (currentRoom === roomName && socket && connected) {
        socket.send(JSON.stringify({
          type: 'user_leave',
          username: user?.username
        }));
        await new Promise(resolve => setTimeout(resolve, 100));
        
        await axios.post(`/api/rooms/${roomName}/leave/`);
        
        if (socket) {
          socket.close();
        }
        setCurrentRoom('');
        setCurrentRoomInfo(null);
        setMessages([]);
        setMessage('');
        setConnected(false);
        setSocket(null);
      } else {
        const tempWs = new WebSocket(`ws://localhost:8000/ws/chat/${roomName}/`);
        
        tempWs.onopen = () => {
          tempWs.send(JSON.stringify({
            type: 'user_leave',
            username: user?.username
          }));
          
          setTimeout(() => {
            tempWs.close();
          }, 200);
        };
        
        tempWs.onerror = (error) => {
          console.error('임시 WebSocket 오류:', error);
        };
        
        await axios.post(`/api/rooms/${roomName}/leave/`);
      }
      
      fetchMyRooms();
      alert('방에서 나갔습니다.');
      
    } catch (error) {
      console.error('방 나가기 실패:', error);
      alert('방 나가기에 실패했습니다.');
    }
  };

  const handleDisconnectRoom = async () => {
    const roomName = currentRoom;

    try {
      if (roomName && isAuthenticated) {
        await axios.post(`/api/rooms/${roomName}/disconnect/`);
      }
    } catch (error) {
      console.error('서버 연결 해제 알림 실패:', error);
    }

    if (socket) {
      socket.close();
    }
    
    setCurrentRoom('');
    setCurrentRoomInfo(null);
    setMessages([]);
    setConnected(false);
    setSocket(null);
    setMessage('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      if (!isAuthenticated) {
        handleLogin();
      } else if (currentRoom) {
        handleSendMessage();
      } else if (roomName) {
        handleJoinRoom(roomName);
      }
    }
  };

  // useEffect들 - 실행 순서대로 배치
  
  // 1. 초기화 (가장 먼저 실행)
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const savedUser = localStorage.getItem('user');
        
        if (token && savedUser) {
          setAuthToken(token);
          const userData = JSON.parse(savedUser);
          setUser(userData);
          setIsAuthenticated(true);
          
          // 토큰 유효성 검사
          try {
            await axios.get('/api/auth/profile/');
            // 🔥 토큰이 유효하면 글로벌 WebSocket 연결
            connectGlobalSocket(userData);
          } catch (error) {
            setAuthToken(null);
            setUser(null);
            setIsAuthenticated(false);
          }
        }
      } catch (error) {
        console.error('인증 초기화 실패:', error);
        setAuthToken(null);
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, [setAuthToken]); // 🔥 connectGlobalSocket 의존성 제거

  // 2. 데이터 로드 (초기화 후)
  useEffect(() => {
    fetchRooms();
    fetchMyRooms();
    fetchStats();
  }, [fetchRooms, fetchMyRooms, fetchStats]);

  // 3. 정기 데이터 새로고침 (인증 상태 확인 후)
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      fetchRooms();
      fetchMyRooms();
      fetchStats();
      if (currentRoom) {
        fetchCurrentRoomInfo(currentRoom);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [isAuthenticated, fetchRooms, fetchMyRooms, fetchStats, currentRoom, fetchCurrentRoomInfo]);

  // 4. WebSocket 정리 (컴포넌트 언마운트 시)
  useEffect(() => {
    return () => {
      if (socket) {
        socket.close();
      }
      if (globalSocketRef.current) {
        globalSocketRef.current.close();
      }
    };
  }, [socket]);

  // 5. 읽음 처리 (채팅창 활성화 시)
  useEffect(() => {
    if (currentRoom && isAuthenticated) {
      markAsRead(currentRoom);
    }
  }, [currentRoom, isAuthenticated, markAsRead]);

  // 6. 자동 스크롤 (메시지 변경 시)
  useEffect(() => {
    const messagesContainer = document.querySelector('.chat-messages');
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }, [messages]);

  // 7. 즉시 스크롤 (채팅방 입장 시)
  useEffect(() => {
    if (currentRoom && messages.length > 0) {
      setTimeout(() => {
        const messagesContainer = document.querySelector('.chat-messages');
        if (messagesContainer) {
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
      }, 50);
    }
  }, [currentRoom, messages.length]);

  // 로딩 화면
  if (isLoading) {
    return (
      <div className="app">
        <div className="loading-container">
          <div className="spinner"></div>
          <h2>로딩 중...</h2>
          <p>잠시만 기다려주세요</p>
        </div>
      </div>
    );
  }

  // 채팅 화면
  if (currentRoom) {
    return (
      <div className="app chat-app">
        <div className="chat-header">
          <div className="room-info">
            <h1>💬 {currentRoom}</h1>
            <div className="room-details">
              <span className={`status ${connected ? 'online' : 'offline'}`}>
                {connected ? '🟢 연결됨' : '🔴 연결 안됨'}
              </span>
              {currentRoomInfo && (
                <span className="member-count">
                  {currentRoomInfo.current_members || 0}/{currentRoomInfo.max_members || 0}
                </span>
              )}
            </div>
          </div>
          <div className="header-actions">
            <span className="user-name">👋 {user?.username}</span>
            <button onClick={handleLeaveRoom} className="btn btn-secondary">
              방 나가기
            </button>
            <button onClick={handleDisconnectRoom} className="btn btn-outline">
              뒤로가기
            </button>
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">🌟</span>
              <p>첫 번째 메시지를 보내보세요!</p>
            </div>
          ) : messages.map(msg => (
            <div 
              key={msg.id} 
              className={`message ${
                msg.isSystem ? 'system-message' : 
                msg.author === user?.username ? 'my-message' : 'other-message'
              }`}
              data-message-id={msg.message_id}
            >
              <div className="message-header">
                <span className="author">{msg.author}</span>
                <span className="time">{msg.time}</span>
              </div>
              
              {!msg.isSystem ? (
                <>
                  <div className="message-wrapper">
                    <div className="message-bubble">
                      <div className="message-content">{msg.text}</div>
                    </div>
                    
                    <div className="read-status">
                      {msg.author === user?.username ? (
                        msg.unreadCount > 0 && (
                          <span className="unread-count">{msg.unreadCount}</span>
                        )
                      ) : (
                        msg.isReadByAll ? (
                          <span className="read-all"></span>
                        ) : msg.unreadCount > 0 ? (
                          <span className="unread-count">{msg.unreadCount}</span>
                        ) : null
                      )}
                    </div>
                  </div>
                  
                  <MessageReactions 
                    messageId={msg.message_id}
                    currentUser={user?.username}
                    reactions={msg.reactions}
                  />
                </>
              ) : (
                <div className="message-bubble">
                  <div className="message-content">{msg.text}</div>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="message-input">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="메시지를 입력하세요..."
            disabled={!connected}
            className="message-field"
          />
          <button 
            onClick={handleSendMessage} 
            disabled={!connected || !message.trim()}
            className="btn btn-primary"
          >
            전송
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Test 채팅</h1>
        <div className="header-actions">
          <div className="online-stats">
            <span className="stat-icon stat-text">🌱 온라인 수: </span>
            <span className="stat-text">  {stats.online_users || 0}</span>
          </div>
          
          {isAuthenticated ? (
            <div className="user-menu">
              <span className="user-info">👋 {user.username}님</span>
              <button className="btn btn-secondary" onClick={handleLogout}>
                로그아웃
              </button>
            </div>
          ) : (
            <div className="login-section">
              <input
                type="text"
                value={loginForm.username}
                onChange={(e) => setLoginForm({...loginForm, username: e.target.value})}
                onKeyPress={handleKeyPress}
                placeholder="아이디"
                className="login-input"
              />
              <input
                type="password"
                value={loginForm.password}
                onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                onKeyPress={handleKeyPress}
                placeholder="비밀번호"
                className="login-input"
              />
              <button className="btn btn-primary" onClick={handleLogin}>
                로그인
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="main-content">
        {isAuthenticated && myRooms.length > 0 && (
          <section className="my-rooms-section">
            <div className="section-header">
              <h2>🏠 내가 입장한 채팅방</h2>
              <span className="room-count">
                {myRooms.length}개
              </span>
            </div>
            <div className="my-rooms-grid">
              {myRooms
                .sort((a, b) => (b.unread_count || 0) - (a.unread_count || 0)) // 🔥 안읽은 메시지 많은 순으로 정렬
                .map(room => (
                <div key={room.id} className={`my-room-card ${room.unread_count > 0 ? 'has-unread' : ''}`}>
                  <div className="room-header">
                    <h3 className="room-name">
                      {room.name}
                      {room.unread_count > 0 && (<span className="unread-badge">{room.unread_count > 99 ? '99+' : room.unread_count}</span>)}
                    </h3>
                  </div>
                  <p className="room-description">{room.description}</p>
                  <div className="room-info">
                    <span className="room-members">
                      👥 인원수: {room.member_count}/{room.max_members}
                    </span>
                    <span className="last-seen">
                      🕐 마지막 접속: {room.last_seen ? new Date(room.last_seen).toLocaleString() : '미접속'}
                    </span>
                  </div>
                  <div className="room-actions">
                    <button 
                      className={`btn btn-sm ${room.unread_count > 0 ? 'btn-primary btn-glow' : 'btn-primary'}`}
                      onClick={() => handleJoinRoom(room.name)}
                    >
                      {room.unread_count > 0 ? `⚡ 새 메시지 ${room.unread_count}개` : '열기'}
                    </button>
                    <button 
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleLeaveMyRoom(room.name)}
                    >
                      나가기
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {isAuthenticated && (
          <section className="create-section">
            <div className="section-header">
              <h2>✚ 새 방 만들기</h2>
              {!showCreateRoom && (
                <button onClick={() => setShowCreateRoom(true)} className="btn btn-success btn-sm">
                  + 방 만들기
                </button>
              )}
            </div>
            
            {showCreateRoom && (
              <div className="create-form">
                <div className="form-row">
                  <input
                    type="text"
                    placeholder="방 이름"
                    value={roomForm.name}
                    onChange={(e) => setRoomForm({...roomForm, name: e.target.value})}
                    className="form-input"
                  />
                  <input
                    type="number"
                    placeholder="최대 인원"
                    value={roomForm.max_members}
                    onChange={(e) => setRoomForm({...roomForm, max_members: e.target.value})}
                    className="form-input form-input-small"
                    min="1"
                    max="1000"
                  />
                </div>
                <input
                  type="text"
                  placeholder="방 설명 (선택사항)"
                  value={roomForm.description}
                  onChange={(e) => setRoomForm({...roomForm, description: e.target.value})}
                  className="form-input"
                />
                <div className="form-actions">
                  <button onClick={() => setShowCreateRoom(false)} className="btn btn-outline btn-sm">
                    취소
                  </button>
                  <button onClick={handleCreateRoom} className="btn btn-success btn-sm">
                    생성
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        <section className="rooms-section">
          <h2>🌟 모든 채팅방</h2>
          {rooms.length === 0 ? (
            <div className="empty-rooms">
              <p>아직 채팅방이 없습니다.</p>
              {!isAuthenticated && <p>로그인하면 채팅방을 만들 수 있어요!</p>}
            </div>
          ) : (
            <div className="rooms-grid">
              {rooms.map(room => (
                <div key={room.id} className="room-card">
                  <div className="room-header">
                    <h3 className="room-name">{room.name}</h3>
                  </div>
                  <p className="room-description">{room.description}</p>
                  <div className="room-info">
                    <span className="room-members">
                      👥 {room.member_count}/{room.max_members}
                    </span>
                    <span className="room-creator">👤 {room.created_by}</span>
                  </div>
                  <div className="room-footer">
                    <span className="room-date">
                      📅 {new Date(room.created_at).toLocaleDateString()}
                    </span>
                    <button 
                      className="btn btn-primary btn-sm"
                      onClick={() => {
                        setRoomName(room.name);
                        handleJoinRoom(room.name);
                      }}
                      disabled={!isAuthenticated}
                    >
                      입장하기
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;