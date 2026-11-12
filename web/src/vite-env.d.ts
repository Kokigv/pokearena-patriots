/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Client ID de Google Identity Services. Sin él, solo aparece el usuario de prueba. */
  readonly VITE_GOOGLE_CLIENT_ID?: string;
}

interface GoogleCredentialResponse {
  credential: string;
}

interface Window {
  google?: {
    accounts: {
      id: {
        initialize: (options: {
          client_id: string;
          callback: (response: GoogleCredentialResponse) => void;
        }) => void;
        renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
      };
    };
  };
}
