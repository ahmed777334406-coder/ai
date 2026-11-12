import nextVitals from 'eslint-config-next/core-web-vitals';
const config = [...nextVitals, {ignores:['.next/**','node_modules/**','playwright-report/**','test-results/**']}, {rules:{'@next/next/no-img-element':'off','react/no-unescaped-entities':'off','react-hooks/set-state-in-effect':'off'}}];
export default config;
