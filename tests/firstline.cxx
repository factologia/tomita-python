#encoding "utf-8"    // сообщаем парсеру о том, в какой кодировке написана грамматика
#GRAMMAR_ROOT S      // указываем корневой нетерминал грамматики

Line -> Noun<kwtype='линия'>;

// 1-я линия
FirstLine -> AnyWord<wff=/\d+(-?а?я)?/> interp (FirstLine.Line) Line<gram='им', rt>;

// Числительное
FirstLine -> OrdinalNumeral<gnc-agr[1]> interp (FirstLine.Line) Line<gnc-agr[1], gram='им', rt>;
FirstLine -> OrdinalNumeral<gnc-agr[1]> interp (FirstLine.Line) Line<gnc-agr[1], gram='пр', rt>;

S -> FirstLine;           // правило, выделяющее первую линию
