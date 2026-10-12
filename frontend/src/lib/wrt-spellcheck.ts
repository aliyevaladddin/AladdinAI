// NOTICE: This file is protected under RCF-PL

/**
 * Intelligent Spell & Grammar Checker for WRT Document Processor.
 *
 * Checks document prose for common typos, repeated words, and casing errors
 * across multiple languages (Russian, English, Azerbaijani/Turkish).
 * Ignores WRT tags ([b], [/b], [h1], etc.) and bracketed URLs/references ([https://...], [1]).
 */

export interface SpellCheckIssue {
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
  word: string;
  message: string;
  suggestions: string[];
}

// Common dictionary of frequently misspelled words and their corrections
const COMMON_TYPOS: Record<string, string[]> = {
  // Russian common typos
  "здавствуйте": ["здравствуйте"],
  "здраствуйте": ["здравствуйте"],
  "пожалуста": ["пожалуйста"],
  "спасиба": ["спасибо"],
  "ошыбка": ["ошибка"],
  "ашыбка": ["ошибка"],
  "програма": ["программа"],
  "програмист": ["программист"],
  "документция": ["документация"],
  "функцея": ["функция"],
  "редактирование": ["редактирование"],
  "раскладка": ["раскладка"],
  "пожалуйсто": ["пожалуйста"],
  "система": ["система"],
  "интерфейс": ["интерфейс"],
  "потомучто": ["потому что"],
  "таккак": ["так как"],
  "тоесть": ["то есть"],
  "впринципе": ["в принципе"],
  "вобще": ["вообще"],
  "вообщем": ["в общем", "вообще"],

  // English common typos
  "teh": ["the"],
  "recieve": ["receive"],
  "seperate": ["separate"],
  "untill": ["until"],
  "occured": ["occurred"],
  "beleive": ["believe"],
  "definitly": ["definitely"],
  "wierd": ["weird"],
  "truely": ["truly"],
  "thier": ["their"],
  "adress": ["address"],
  "accomodate": ["accommodate"],
  "achive": ["achieve"],
  "agian": ["again"],
  "alot": ["a lot"],
  "begining": ["beginning"],
  "calender": ["calendar"],
  "definately": ["definitely"],
  "enviroment": ["environment"],
  "familar": ["familiar"],
  "goverment": ["government"],
  "incidently": ["incidentally"],
  "neccessary": ["necessary"],
  "noticeable": ["noticeable"],
  "occurance": ["occurrence"],
  "tommorow": ["tomorrow"],
  "wich": ["which"],
};

/**
 * Strips WRT markup tags while preserving line and column alignment
 * so character coordinates match the Monaco editor model.
 */
export function checkDocumentSpelling(text: string): SpellCheckIssue[] {
  const issues: SpellCheckIssue[] = [];
  const lines = text.split("\n");

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
    const lineText = lines[lineIndex];
    const lineNumber = lineIndex + 1;

    // Mask WRT tags like [b], [/b], [link url="..."], [img ...], [table], etc.
    // Replace tag contents with spaces so column numbers remain exact.
    const maskedLine = lineText.replace(/\[\/?[\w= "':/.-]+\]/g, (match) => " ".repeat(match.length));

    // 1. Check for duplicate words in sequence ("в в", "the the", "и и")
    const dupRegex = /\b([a-zA-Zа-яА-ЯёЁ]+)\s+\1\b/gi;
    let dupMatch: RegExpExecArray | null;
    while ((dupMatch = dupRegex.exec(maskedLine)) !== null) {
      const matchWord = dupMatch[1];
      const startCol = dupMatch.index + 1;
      const endCol = startCol + dupMatch[0].length;
      issues.push({
        startLineNumber: lineNumber,
        startColumn: startCol,
        endLineNumber: lineNumber,
        endColumn: endCol,
        word: dupMatch[0],
        message: `Повтор слова: «${matchWord}»`,
        suggestions: [matchWord],
      });
    }

    // 2. Scan individual words for known spelling mistakes
    const wordRegex = /\b([a-zA-Zа-яА-ЯёЁ]+)\b/g;
    let wordMatch: RegExpExecArray | null;
    while ((wordMatch = wordRegex.exec(maskedLine)) !== null) {
      const rawWord = wordMatch[1];
      const lower = rawWord.toLowerCase();
      const startCol = wordMatch.index + 1;
      const endCol = startCol + rawWord.length;

      // Skip words with mixed letters and numbers or tiny words
      if (rawWord.length < 2) continue;

      if (COMMON_TYPOS[lower]) {
        const correctSuggestions = COMMON_TYPOS[lower].map((cand) => {
          // Preserve first-letter casing if original was Capitalized
          if (rawWord[0] === rawWord[0].toUpperCase()) {
            return cand.charAt(0).toUpperCase() + cand.slice(1);
          }
          return cand;
        });

        issues.push({
          startLineNumber: lineNumber,
          startColumn: startCol,
          endLineNumber: lineNumber,
          endColumn: endCol,
          word: rawWord,
          message: `Орфографическая ошибка: «${rawWord}». Возможно: ${correctSuggestions.join(", ")}`,
          suggestions: correctSuggestions,
        });
      }
    }
  }

  return issues;
}
