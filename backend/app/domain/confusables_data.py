"""Look-alike letters that fold to ASCII, generated from Unicode TR39 confusables.txt (US-102).

Source: https://www.unicode.org/Public/security/latest/confusables.txt, version 18.0.0.
Unicode data files are used under the Unicode License (https://www.unicode.org/license.txt).
Do not edit by hand: regenerate with `scripts/gen_confusables.py` (see its docstring).
"""

# ASCII character -> the non-ASCII characters that look like it.
_GROUPS: dict[str, str] = {
    "1": ("\u0661\u06f1\U0001e141"),
    "2": ("\u01a7\u03e8\u10c7\u14bf\u1616\u1cb7\ua644\ua6ef\ua75a"),
    "3": (
        "\u01b7\u021c\u0417\u04e0\u0545\u0969\u0ae9\u1702\u1c95\u2c9c\u2cc4\u2ccc\ua76a\ua7ab"
        "\U000118ca\U00016f3b"
    ),
    "4": ("\u13ce\uab9e\U000118af\U00016e82"),
    "5": ("\u01bc\U000118bb"),
    "6": ("\u03ec\u0431\u13ee\u2cd2\u2cd3\u2cdc\ua543\uabbe\U000118d5"),
    "7": ("\u172a\u1c84\U000104d2\U000118c6\U00016e8a"),
    "8": ("\u0222\u0223\u09ea\u0a6a\ua589\U0001031a\U000169fe\U0001e8cb"),
    "9": (
        "\u09ed\u0a67\u0b68\u0d6d\u2cca\u2ccb\ua76e\ua76f\U000118ac\U000118cc\U000118d6\U000169c1\U0001e2f2"
    ),
    "A": (
        "\u0391\u0410\u13aa\u15c5\ua4ee\U000102a0\U00016f40\U0001d6a8\U0001d6e2\U0001d71c\U0001d756\U0001d790"
    ),
    "AA": ("\ua732"),
    "AE": ("\u00c6\u04d4"),
    "AO": ("\ua734"),
    "AU": ("\ua736"),
    "AV": ("\ua738\ua73a"),
    "AY": ("\ua73c"),
    "B": (
        "\u0392\u0412\u13f4\u15f7\u2c82\ua4d0\ua557\ua7b4\U00010282\U000102a1\U00010301\U0001d6a9"
        "\U0001d6e3\U0001d71d\U0001d757\U0001d791"
    ),
    "C": ("\u03f9\u0421\u13df\u2ca4\ua4da\U000102a2\U00010302\U00010415\U0001051b\U000118e9\U000118f2"),
    "D": ("\u13a0\u15de\u15ea\ua4d3"),
    "E": (
        "\u0395\u0415\u13ac\u2d39\ua4f0\ua5cb\U00010286\U000118a6\U000118ae\U0001d6ac\U0001d6e6"
        "\U0001d720\U0001d75a\U0001d794"
    ),
    "F": ("\u03dc\u07d3\u15b4\ua4dd\ua798\U00010287\U000102a5\U00010525\U000118a2\U000118c2\U0001d7ca"),
    "G": ("\u050c\u13c0\u13f3\ua4d6"),
    "H": ("\u0397\u041d\u13bb\u157c\u2c8e\ua4e7\U000102cf\U0001d6ae\U0001d6e8\U0001d722\U0001d75c\U0001d796"),
    "I": ("\u0196\u0399\u0406\u04c0\u2c92\ua7ae\U00010ca5\U0001d6b0\U0001d6ea\U0001d724\U0001d75e\U0001d798"),
    "J": ("\u037f\u0408\u13ab\u148d\ua4d9\ua7b2"),
    "K": ("\u039a\u041a\u13e6\u16d5\u2c94\ua4d7\U00010518\U0001d6b1\U0001d6eb\U0001d725\U0001d75f\U0001d799"),
    "L": ("\u13de\u14aa\u2cd0\ua4e1\U0001041b\U00010526\U000118a3\U000118b2\U00016f16"),
    "M": (
        "\u039c\u03fa\u041c\u13b7\u15f0\u16d6\u2c98\ua4df\U000102b0\U00010311\U00010c21\U0001d6b3"
        "\U0001d6ed\U0001d727\U0001d761\U0001d79b"
    ),
    "N": ("\u039d\u2c9a\ua4e0\U00010513\U00011abe\U0001d6b4\U0001d6ee\U0001d728\U0001d762\U0001d79c"),
    "O": (
        "\u039f\u041e\u0555\u07c0\u0b20\u0ce6\u12d0\u1cbf\u2c9e\u2d54\u3007\ua4f3\U00010292"
        "\U000102ab\U0001030f\U00010404\U000104c2\U00010516\U00010c17\U000118b5\U000118e0\U00016ae9"
        "\U0001d6b6\U0001d6f0\U0001d72a\U0001d764\U0001d79e\U0001e140\U0001e2f0"
    ),
    "OE": ("\u0152"),
    "OO": ("\ua698\ua74e"),
    "Oy": ("\u0478"),
    "P": (
        "\u03a1\u0420\u13e2\u146d\u2ca2\u2cce\ua4d1\U00010295\U0001d6b8\U0001d6f2\U0001d72c"
        "\U0001d766\U0001d7a0"
    ),
    "Q": ("\u051a\u2d55"),
    "R": ("\u01a6\u024c\u13a1\u13d2\u1587\ua4e3\U000104b4\U00016f35"),
    "S": ("\u0405\u054f\u10bd\u10fd\u13d5\u13da\u1cbd\ua4e2\ua576\U00010296\U00010420\U00016ad6\U00016f3a"),
    "T": (
        "\u03a4\u0422\u07e0\u13a2\u2ca6\u3112\u4e05\ua4d4\ua50b\U00010297\U000102b1\U00010315"
        "\U000118bc\U00016f0a\U0001d373\U0001d6bb\U0001d6f5\U0001d72f\U0001d769\U0001d7a3"
    ),
    "T3": ("\ua728"),
    "U": ("\u054d\u1200\u144c\ua4f4\U000104ce\U000118b8\U00016f42"),
    "V": (
        "\u0474\u0667\u06f7\u13d9\u142f\u2d38\ua4e6\ua6df\U0001051d\U00010c1f\U000118a0\U00016f08\U0001e145"
    ),
    "W": ("\u051c\u13b3\u13d4\ua4ea\U000118e6\U000118ef"),
    "X": (
        "\u03a7\u0425\u16b7\u1cf5\u2cac\u2d5d\ua4eb\ua7b3\U00010290\U000102b4\U00010317\U00010322"
        "\U00010527\U00010c13\U00010c82\U00010cfc\U000118ec\U0001d6be\U0001d6f8\U0001d732\U0001d76c"
        "\U0001d7a6"
    ),
    "Y": (
        "\u03a5\u03d2\u0423\u04ae\u07cc\u13a9\u13bd\u2ca8\u311a\u4e2b\ua4ec\U000102b2\U00010c20"
        "\U000118a4\U00016f43\U0001d6bc\U0001d6f6\U0001d730\U0001d76a\U0001d7a4"
    ),
    "Z": (
        "\u0396\u10cd\u13c3\u2c6b\u2c8c\ua4dc\ua6c9\U000102f5\U00010507\U000118a9\U000118e5"
        "\U00011abc\U0001d6ad\U0001d6e7\U0001d721\U0001d75b\U0001d795"
    ),
    "a": ("\u0251\u03b1\u0430\uab64\U0001d6c2\U0001d6fc\U0001d736\U0001d770\U0001d7aa"),
    "aa": ("\ua733"),
    "ae": ("\u00e6\u04d5"),
    "ao": ("\ua735"),
    "au": ("\ua737"),
    "av": ("\ua739\ua73b"),
    "ay": ("\ua73d"),
    "b": ("\u0184\u042c\u07d5\u13cf\u1472\u15af\U0001031c"),
    "bl": ("\u042b"),
    "c": ("\u03f2\u0441\u1004\u105a\u1c83\u1d04\u2ca5\uabaf\U0001043d"),
    "co": ("\uab43"),
    "d": ("\u0501\u13e7\u146f\ua4d2\U0001018b"),
    "dz": ("\u02a3"),
    "e": ("\u0435\u04bd\uab32"),
    "f": ("\u0192\u0284\u0584\u1e9d\ua799\uab35"),
    "g": ("\u018d\u0261\u0581\u1d83"),
    "h": ("\u04ba\u04bb\u0570\u10b9\u13c2"),
    "i": (
        "\u0131\u0269\u026a\u03b9\u0456\u0582\u13a5\u2c93\ua647\uab75\U000118c3\U0001d6a4\U0001d6ca"
        "\U0001d704\U0001d73e\U0001d778\U0001d7b2"
    ),
    "j": ("\u0237\u03f3\u0458\u0575\U0001d6a5"),
    "l": (
        "\u01c0\u04cf\u05d5\u05df\u0627\u07ca\u16c1\u16d0\u2d4a\u2d4f\ua4f2\ua56f\ua781\ua7fe\ua830"
        "\ufe8d\ufe8e\U0001028a\U00010309\U00010320\U0001050e\U00010926\U00010c3e\U00010cfa"
        "\U00016f28\U0001d377\U0001e8c7\U0001ed01\U0001ee00\U0001ee80"
    ),
    "lL": ("\u1efa"),
    "lO": ("\u042e"),
    "ll": ("\u01c1\u05f0"),
    "lll": ("\ua516"),
    "ls": ("\u02aa"),
    "lz": ("\u02ab"),
    "n": ("\u0578\u057c"),
    "o": (
        "\u03bf\u03c3\u03ed\u043e\u0585\u05e1\u0647\u0665\u06be\u06c1\u06d5\u06f5\u07cb\u0840\u0966"
        "\u09e6\u0a66\u0ae6\u0b66\u0be6\u0c66\u0d20\u0d66\u0e50\u0ed0\u101d\u1040\u10ff\u110b\u11bc"
        "\u17e0\u1a45\u1a80\u1a90\u1c82\u1d0f\u1d11\u2c9f\u3147\uab3d\ufba6\ufba7\ufba8\ufba9\ufbaa"
        "\ufbab\ufbac\ufbad\ufee9\ufeea\ufeeb\ufeec\uffb7\U0001042c\U000104ea\U0001092c\U00010d07"
        "\U00011124\U000114d0\U000118c8\U000118d7\U0001d6d0\U0001d6d4\U0001d70a\U0001d70e\U0001d744"
        "\U0001d748\U0001d77e\U0001d782\U0001d7b8\U0001d7bc\U0001ee24\U0001ee84"
    ),
    "oe": ("\u0153"),
    "ol": ("\U0001ee64"),
    "oo": ("\u1147\u11ee\u3180\ua699\ua74f"),
    "oy": ("\u0479"),
    "p": (
        "\u00fe\u01bf\u03c1\u03f1\u03f8\u0440\u2ca3\u2ccf\U0001d6d2\U0001d6e0\U0001d70c\U0001d71a"
        "\U0001d746\U0001d754\U0001d780\U0001d78e\U0001d7ba\U0001d7c8"
    ),
    "q": ("\u051b\u0563\u0566"),
    "r": ("\u0433\u1d26\u2c85\uab47\uab48\uab81\U00016a19"),
    "rn": ("\u0560\U00011700\U000118e3"),
    "s": ("\u01bd\u0455\u0d1f\ua731\uabaa\U00010448\U000118c1"),
    "tf": ("\ua777"),
    "ts": ("\u02a6"),
    "u": (
        "\u028b\u03c5\u057d\u1d1c\ua79f\uab4e\uab52\U000104f6\U000118d8\U0001d6d6\U0001d710"
        "\U0001d74a\U0001d784\U0001d7be"
    ),
    "ue": ("\u1d6b"),
    "uo": ("\uab63"),
    "v": (
        "\u03bd\u0475\u05d8\u1d20\uaba9\U00011706\U000118c0\U0001d6ce\U0001d708\U0001d742\U0001d77c\U0001d7b6"
    ),
    "w": ("\u026f\u0448\u0461\u051d\u0561\u1d21\u2cbd\ua7fa\uab83\uaba4\U0001170a\U0001170e\U0001170f"),
    "x": ("\u0445\u1541\u157d\u1763\U00010cc2"),
    "y": (
        "\u0263\u028f\u03b3\u0443\u04af\u10e7\u1d8c\u1eff\u213d\u2ca9\uab5a\U000118c4\U000118dc"
        "\U0001d6c4\U0001d6fe\U0001d738\U0001d772\U0001d7ac"
    ),
    "z": ("\u1d22\u2c6c\u2c8d\u2d2d\uab93"),
}

CONFUSABLES: dict[int, str] = {ord(src): ascii_char for ascii_char, group in _GROUPS.items() for src in group}
