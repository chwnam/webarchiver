python-web-archiver
===================
my tool for scrap html pages

웹 상의 HTML 문서를 수집하고 파싱을 할 때 Requests 라이브러리나 BeautifulSoup 라이브러리를 이용하면 매우 간단하게 처리가 가능하지만,
때때로 웹상의 자원을 수집할 때에는 이런저런 사소한 문제들을 겪곤 한다.

예를 들어 Requests 라이브러리 자체는 매우 훌륭하지만, 때로는 쿠키를 직접적으로 관리하려면 손이 많이 가고, 또 때로는 어떤 웹사이트들은 자바스크립트 처리가 많아
단순 URL 접근 및 HTML 문서 해독만으로는 어려운 경우도 있다. 이 때는 자바스크립트를 지원하는 PhantomJS 같은 라이브러리를 사용하는 것이 좋은데,
만일 Requests를 사용하던 중이었다면 갑자기 PhantomJS로 넘어가기엔 기존 작성된 코드와의 충돌도 감수해야 할 것이다.

이렇게 여러 라이브러리를 섞어 쓰는 경우 자잘한 디테일을 처리하기 위한 python-web-archiver 라이브러리를 만들어 보았다.
여러 웹상의 접근하기 위한 라이브러리를 Connector 개념으로 묶어 손쉽게 get, post 요청으로 가져올 수 있도록 했다.

Connector 종류는 현재 2가지가 있다.

* RequestsConnector: Requests 라이브러리를 이용한 커넥터
* PhantomJSConnector: PhantomJS 라이브러리르 이용한 커넥터. 실제 웹브라우저이므로 조금 무겁기는 하지만 웹브라우저를 그대로 쓰므로 매우 강력해진다.

이외에 웹의 여러 URL을 다운로드 받고, 그 파일들을 zip이나 tar.gz로 압축하는 기능을 가지고 있다.
