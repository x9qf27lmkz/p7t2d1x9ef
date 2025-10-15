// src/hooks/usekakaoloader.js
import { useEffect, useMemo, useState } from "react";

/**
 * 내부 싱글톤 상태 (여러 컴포넌트가 동시에 써도 스크립트는 1번만 붙음)
 */
let _loadPromise = null;
let _scriptEl = null;

function buildSdkUrl({ appkey, libraries = [] }) {
  const params = new URLSearchParams({
    appkey,
    autoload: "false", // 반드시 false 후 maps.load로 로딩
  });
  if (libraries.length > 0) {
    params.set("libraries", libraries.join(","));
  }
  return `https://dapi.kakao.com/v2/maps/sdk.js?${params.toString()}`;
}

/**
 * 카카오 SDK 로드(싱글톤). maps.load 까지 완료되면 resolve.
 * - 이미 로드 중/완료라면 기존 프라미스를 재사용한다.
 */
function ensureKakaoLoaded({ appkey, libraries }) {
  if (_loadPromise) return _loadPromise;

  _loadPromise = new Promise((resolve, reject) => {
    // 이미 window.kakao가 있고 load가 끝난 경우
    if (typeof window !== "undefined" && window.kakao?.maps) {
      // kakao.maps.load 이 존재하면 한번 더 감싼다
      if (typeof window.kakao.maps.load === "function") {
        window.kakao.maps.load(() => resolve(window.kakao));
      } else {
        resolve(window.kakao);
      }
      return;
    }

    // 스크립트 생성
    try {
      _scriptEl = document.createElement("script");
      _scriptEl.async = true;
      _scriptEl.src = buildSdkUrl({ appkey, libraries });
      _scriptEl.onload = () => {
        // autoload=false 이므로 여기서 load 호출
        if (!window.kakao?.maps?.load) {
          reject(new Error("Kakao SDK loaded but kakao.maps.load is missing"));
          return;
        }
        window.kakao.maps.load(() => resolve(window.kakao));
      };
      _scriptEl.onerror = () => {
        reject(new Error("Failed to load Kakao SDK"));
      };
      document.head.appendChild(_scriptEl);
    } catch (e) {
      reject(e);
    }
  });

  return _loadPromise;
}

/**
 * React 훅:
 * - EXPO_PUBLIC_KAKAO_JS_KEY 에서 키를 읽는다
 * - libraries 기본값: ["clusterer"]
 * - ready(불린), kakao(window.kakao), error를 반환
 * - withKakao(cb) 유틸도 함께 반환 (준비 전이면 알아서 기다렸다 호출)
 */
export default function useKakaoLoader(options = {}) {
  const appkey = options.appkey ?? process.env.EXPO_PUBLIC_KAKAO_JS_KEY;
  const libraries = options.libraries ?? ["clusterer"];

  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  // withKakao 유틸: kakao 준비 후 콜백 실행
  const withKakao = useMemo(() => {
    return async (cb) => {
      try {
        const kakao = await ensureKakaoLoaded({ appkey, libraries });
        if (typeof cb === "function") cb(kakao);
      } catch (e) {
        // 호출 측에서 별도 처리 원하면 throw
        throw e;
      }
    };
  }, [appkey, libraries]);

  useEffect(() => {
    let alive = true;

    if (!appkey) {
      setError(new Error("Kakao JS Key is missing (EXPO_PUBLIC_KAKAO_JS_KEY)"));
      setReady(false);
      return () => {};
    }

    ensureKakaoLoaded({ appkey, libraries })
      .then(() => {
        if (!alive) return;
        setReady(true);
        setError(null);
      })
      .catch((e) => {
        if (!alive) return;
        setReady(false);
        setError(e);
        // 필요시 스크립트 제거 (다음 시도에서 재로딩 가능)
        try {
          if (_scriptEl?.parentNode) _scriptEl.parentNode.removeChild(_scriptEl);
        } catch {}
        _loadPromise = null;
        _scriptEl = null;
      });

    return () => {
      alive = false;
      // 스크립트는 글로벌로 공유하므로 일반적으로 제거하지 않는다.
      // (HMR/탭 간 공유/다수 컴포넌트 재사용 고려)
    };
  }, [appkey, libraries]);

  return {
    ready,
    error,
    kakao: typeof window !== "undefined" ? window.kakao : undefined,
    withKakao,
  };
}

/**
 * 훅 외부(비리액트)에서도 쓰고 싶다면 이 함수 export해서 await 가능
 */
export async function loadKakaoOnce(opts = {}) {
  const appkey = opts.appkey ?? process.env.EXPO_PUBLIC_KAKAO_JS_KEY;
  const libraries = opts.libraries ?? ["clusterer"];
  return ensureKakaoLoaded({ appkey, libraries });
}
