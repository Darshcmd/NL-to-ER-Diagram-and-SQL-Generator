import React, { createContext, useReducer, useCallback } from 'react';

const SchemaContext = createContext();

const initialState = {
  sessionId: null,
  nlInput: '',
  fileContext: '',
  clarifyingQuestions: [],
  currentMermaid: null,
  currentSchema: null,
  sqlCode: null,
  chatHistory: [],
  loading: false,
  error: null,
  analysisSummary: '',
};

function schemaReducer(state, action) {
  switch (action.type) {
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    case 'SET_INPUT':
      return { ...state, nlInput: action.payload };
    case 'SET_FILE_CONTEXT':
      return { ...state, fileContext: action.payload };
    case 'SET_QUESTIONS':
      return { ...state, clarifyingQuestions: action.payload };
    case 'SET_MERMAID':
      return { ...state, currentMermaid: action.payload };
    case 'SET_SCHEMA':
      return { ...state, currentSchema: action.payload };
    case 'SET_SQL':
      return { ...state, sqlCode: action.payload };
    case 'ADD_TO_CHAT':
      return {
        ...state,
        chatHistory: [...state.chatHistory, action.payload],
      };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_SUMMARY':
      return { ...state, analysisSummary: action.payload };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function SchemaProvider({ children }) {
  const [state, dispatch] = useReducer(schemaReducer, initialState);

  const actions = {
    setSessionId: useCallback((id) => {
      dispatch({ type: 'SET_SESSION_ID', payload: id });
    }, []),
    setInput: useCallback((text) => {
      dispatch({ type: 'SET_INPUT', payload: text });
    }, []),
    setFileContext: useCallback((text) => {
      dispatch({ type: 'SET_FILE_CONTEXT', payload: text });
    }, []),
    setQuestions: useCallback((questions) => {
      dispatch({ type: 'SET_QUESTIONS', payload: questions });
    }, []),
    setMermaid: useCallback((mermaid) => {
      dispatch({ type: 'SET_MERMAID', payload: mermaid });
    }, []),
    setSchema: useCallback((schema) => {
      dispatch({ type: 'SET_SCHEMA', payload: schema });
    }, []),
    setSql: useCallback((sql) => {
      dispatch({ type: 'SET_SQL', payload: sql });
    }, []),
    addToChat: useCallback((message) => {
      dispatch({ type: 'ADD_TO_CHAT', payload: message });
    }, []),
    setLoading: useCallback((loading) => {
      dispatch({ type: 'SET_LOADING', payload: loading });
    }, []),
    setError: useCallback((error) => {
      dispatch({ type: 'SET_ERROR', payload: error });
    }, []),
    setSummary: useCallback((summary) => {
      dispatch({ type: 'SET_SUMMARY', payload: summary });
    }, []),
    reset: useCallback(() => {
      dispatch({ type: 'RESET' });
    }, []),
  };

  return (
    <SchemaContext.Provider value={{ state, ...actions }}>
      {children}
    </SchemaContext.Provider>
  );
}

export default SchemaContext;
