console.error('✅ Appstore MCP server pronto!');

process.stdin.setEncoding('utf8');
process.stdin.on('data', (data) => {
  console.log('📨 Input MCP ricevuto:', data.trim());
  // Simula risposta MCP
  console.log(JSON.stringify({
    content: [{ type: 'text', text: 'MCP tool "list-apps" eseguito!' }]
  }));
});

process.stdin.on('end', () => {
  console.error('🔌 MCP connection chiusa');
});
