import React from 'react';
import { SchemaProvider } from './context/SchemaContext';
import { MainApp } from './components/MainApp';
import './index.css';

function App() {
  return (
    <SchemaProvider>
      <MainApp />
    </SchemaProvider>
  );
}

export default App;
