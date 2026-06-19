declare module "jsmediatags" {
  interface Tags {
    title?: string;
    artist?: string;
    album?: string;
    year?: string;
    genre?: string;
    track?: string;
    picture?: {
      format: string;
      data: number[];
    };
    lyrics?: {
      lyrics: string;
      description?: string;
    };
  }

  interface SuccessCallback {
    (tag: { tags: Tags }): void;
  }

  interface ErrorCallback {
    (error: { info: string }): void;
  }

  class Reader {
    read(file: File | Blob, callbacks: { onSuccess: SuccessCallback; onError: ErrorCallback }): void;
  }

  const jsmediatags: {
    read(file: File | Blob, callbacks: { onSuccess: SuccessCallback; onError: ErrorCallback }): void;
    Reader: typeof Reader;
  };

  export default jsmediatags;
}
