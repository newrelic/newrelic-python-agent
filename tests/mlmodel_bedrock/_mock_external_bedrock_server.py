# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import re

from testing_support.mock_external_http_server import MockExternalHTTPServer

# This defines an external server test apps can make requests to instead of
# the real Bedrock backend. This provides 3 features:
#
# 1) This removes dependencies on external websites.
# 2) Provides a better mechanism for making an external call in a test app than
#    simple calling another endpoint the test app makes available because this
#    server will not be instrumented meaning we don't have to sort through
#    transactions to separate the ones created in the test app and the ones
#    created by an external call.
# 3) This app runs on a separate thread meaning it won't block the test app.

RESPONSES = {
    "amazon.titan-text-express-v1::Command: Write me a blog about making strong business decisions as a leader.": [
        {},
        {
            "inputTextTokenCount": 19,
            "results": [
                {
                    "tokenCount": 128,
                    "outputText": " Making strong business decisions as a leader requires a combination of strategic thinking, data analysis, and intuition. Here are some tips to help you make informed and effective decisions:\nDefine your goals and vision: Clearly understand your organization's goals and vision, and ensure that all decision-making aligns with these objectives. This will provide a roadmap for your decisions and help you stay focused on the bigger picture.\nGather relevant data and information: Collect and analyze data related to the decision you need to make. Consider multiple sources of information, such as market trends, financial reports, and stakeholder feedback. Use data to inform your decision-making process",
                    "completionReason": "LENGTH",
                }
            ],
        },
    ],
    "anthropic.claude-instant-v1::Human: Write me a blog about making strong business decisions as a leader.": [
        {},
        {
            "completion": " Here is a draft blog post on making strong business decisions as a leader:\n\nTitle: 5 Tips for Making Strong Business Decisions as a Leader\n\nBeing a leader means that tough business decisions will inevitably land on your desk. How you handle those decisions can have a huge impact on your company's success. Here are some tips to help you make strong, informed choices that move your business in the right direction.\n\n1. Gather all relevant data. Don't make a call until you've examined the issue from every angle. Seek out useful metrics, get feedback from various stakeholders, and look at historical trends and precedents. The more data you have, the clearer the right path will become. \n\n2. Consider both short and long-term implications. While it's important to address immediate needs, don't lose sight of how a decision may impact the future. Will your choice simply solve today's problem or help build sustainable growth? Carefully weigh short-term gains against potential long-term consequences.\n\n3. Trust your instincts but don't decide alone. Your gut feelings are valuable, but they shouldn't be the sole basis for a leadership decision. Consult with your management team and get differing perspectives. Encourage respectful debate to surface any risks or uncertainties that need discussion. \n\n4. Be willing todelaya decisionif youneed moretime.There'snobenefittomakingarushjudgement beforeallfactorshavebeenweighed.It'sbettertoletyourdecision\"bake\"athirdopinionormoredataratherthanpotentiallyregrettingahastycalllater.\n\n5. Follow through on the outcome. A good decision means little without effective implementation. Clearly communicate the rationale for your choice and gain organizational buy-in. Then follow up to ensure your solution is executed properly and intended goals are achieved. Are any adjustments needed along the way? \n\nLeaders are entrusted to make the calls that steer a business. With care, research and an open yet discerning approach, you can make decisions that propel your company confidently into the future.",
            "stop_reason": "stop_sequence",
        },
    ],
    "ai21.j2-mid-v1::Write me a blog about making strong business decisions as a leader.": [
        {},
        {
            "id": 1234,
            "prompt": {
                "text": "Write me a blog about making strong business decisions as a leader.",
                "tokens": [
                    {
                        "generatedToken": {
                            "token": "\u2581Write",
                            "logprob": -10.650314331054688,
                            "raw_logprob": -10.650314331054688,
                        },
                        "topTokens": None,
                        "textRange": {"start": 0, "end": 5},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581me",
                            "logprob": -5.457987308502197,
                            "raw_logprob": -5.457987308502197,
                        },
                        "topTokens": None,
                        "textRange": {"start": 5, "end": 8},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581a\u2581blog",
                            "logprob": -8.36896800994873,
                            "raw_logprob": -8.36896800994873,
                        },
                        "topTokens": None,
                        "textRange": {"start": 8, "end": 15},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581about\u2581making",
                            "logprob": -14.223419189453125,
                            "raw_logprob": -14.223419189453125,
                        },
                        "topTokens": None,
                        "textRange": {"start": 15, "end": 28},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581strong",
                            "logprob": -9.367725372314453,
                            "raw_logprob": -9.367725372314453,
                        },
                        "topTokens": None,
                        "textRange": {"start": 28, "end": 35},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581business\u2581decisions",
                            "logprob": -7.66295862197876,
                            "raw_logprob": -7.66295862197876,
                        },
                        "topTokens": None,
                        "textRange": {"start": 35, "end": 54},
                    },
                    {
                        "generatedToken": {
                            "token": "\u2581as\u2581a\u2581leader",
                            "logprob": -13.765915870666504,
                            "raw_logprob": -13.765915870666504,
                        },
                        "topTokens": None,
                        "textRange": {"start": 54, "end": 66},
                    },
                    {
                        "generatedToken": {
                            "token": ".",
                            "logprob": -10.953210830688477,
                            "raw_logprob": -10.953210830688477,
                        },
                        "topTokens": None,
                        "textRange": {"start": 66, "end": 67},
                    },
                ],
            },
            "completions": [
                {
                    "data": {
                        "text": "\nWhen you are a leader at work, you need to make timely and informed decisions on behalf of your team or company. You have to consider multiple factors and variables, and analyze data in a way to make the best possible choice.\n\nHowever, sometimes things don't turn out the way you intended. Your decision might not work as intended, or act in unforeseen ways. Or, you might find new information or context that causes you to question your decision. That's okay.\n\nIt's important to have courage when you're a leader. This means being willing to think critically, reflect, learn from mistakes, and take action steps moving forward.\n\nThere are three steps that can help you grow as a leader and make better business decisions:\n\nStep 1: Gather information\n\nThe first step to making a good decision is to make sure that you have all of the facts. It's important to know what information you need, and from where to get it.\n\nYou can gather information by doing things like reading reports, talking to stakeholders, and conducting research.\n\nStep 2: Analyze information\n\nOnce you've gathered all of your information, you need to take some time to think about it. You need to analyze the data and identify patterns, trends, and trends that might not be immediately obvious.\n\nThere are a few things you should keep in mind when you're analyzing information:\n\n* Identify the key points: What are the key takeaways from this information? What",
                        "tokens": [
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.00011955977242905647,
                                    "raw_logprob": -0.00011955977242905647,
                                },
                                "topTokens": None,
                                "textRange": {"start": 0, "end": 1},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581When\u2581you\u2581are",
                                    "logprob": -6.066172122955322,
                                    "raw_logprob": -6.066172122955322,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1, "end": 13},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581a\u2581leader",
                                    "logprob": -0.8404027223587036,
                                    "raw_logprob": -0.8404027223587036,
                                },
                                "topTokens": None,
                                "textRange": {"start": 13, "end": 22},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581at\u2581work",
                                    "logprob": -8.004234313964844,
                                    "raw_logprob": -8.004234313964844,
                                },
                                "topTokens": None,
                                "textRange": {"start": 22, "end": 30},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.07083408534526825,
                                    "raw_logprob": -0.07083408534526825,
                                },
                                "topTokens": None,
                                "textRange": {"start": 30, "end": 31},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581you\u2581need\u2581to\u2581make",
                                    "logprob": -2.5708985328674316,
                                    "raw_logprob": -2.5708985328674316,
                                },
                                "topTokens": None,
                                "textRange": {"start": 31, "end": 48},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581timely",
                                    "logprob": -9.624330520629883,
                                    "raw_logprob": -9.624330520629883,
                                },
                                "topTokens": None,
                                "textRange": {"start": 48, "end": 55},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and",
                                    "logprob": -1.5508010387420654,
                                    "raw_logprob": -1.5508010387420654,
                                },
                                "topTokens": None,
                                "textRange": {"start": 55, "end": 59},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581informed\u2581decisions",
                                    "logprob": -0.5989360809326172,
                                    "raw_logprob": -0.5989360809326172,
                                },
                                "topTokens": None,
                                "textRange": {"start": 59, "end": 78},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581on\u2581behalf\u2581of",
                                    "logprob": -5.749756336212158,
                                    "raw_logprob": -5.749756336212158,
                                },
                                "topTokens": None,
                                "textRange": {"start": 78, "end": 91},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581your\u2581team",
                                    "logprob": -0.29448866844177246,
                                    "raw_logprob": -0.29448866844177246,
                                },
                                "topTokens": None,
                                "textRange": {"start": 91, "end": 101},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581or",
                                    "logprob": -2.9078853130340576,
                                    "raw_logprob": -2.9078853130340576,
                                },
                                "topTokens": None,
                                "textRange": {"start": 101, "end": 104},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581company",
                                    "logprob": -0.4439607262611389,
                                    "raw_logprob": -0.4439607262611389,
                                },
                                "topTokens": None,
                                "textRange": {"start": 104, "end": 112},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.004392143338918686,
                                    "raw_logprob": -0.004392143338918686,
                                },
                                "topTokens": None,
                                "textRange": {"start": 112, "end": 113},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581You\u2581have",
                                    "logprob": -6.982149600982666,
                                    "raw_logprob": -6.982149600982666,
                                },
                                "topTokens": None,
                                "textRange": {"start": 113, "end": 122},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581to\u2581consider",
                                    "logprob": -2.413727283477783,
                                    "raw_logprob": -2.413727283477783,
                                },
                                "topTokens": None,
                                "textRange": {"start": 122, "end": 134},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581multiple",
                                    "logprob": -2.61666202545166,
                                    "raw_logprob": -2.61666202545166,
                                },
                                "topTokens": None,
                                "textRange": {"start": 134, "end": 143},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581factors",
                                    "logprob": -0.11320021003484726,
                                    "raw_logprob": -0.11320021003484726,
                                },
                                "topTokens": None,
                                "textRange": {"start": 143, "end": 151},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and",
                                    "logprob": -1.4593441486358643,
                                    "raw_logprob": -1.4593441486358643,
                                },
                                "topTokens": None,
                                "textRange": {"start": 151, "end": 155},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581variables",
                                    "logprob": -2.3700382709503174,
                                    "raw_logprob": -2.3700382709503174,
                                },
                                "topTokens": None,
                                "textRange": {"start": 155, "end": 165},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.9362450838088989,
                                    "raw_logprob": -0.9362450838088989,
                                },
                                "topTokens": None,
                                "textRange": {"start": 165, "end": 166},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and\u2581analyze",
                                    "logprob": -7.707818031311035,
                                    "raw_logprob": -7.707818031311035,
                                },
                                "topTokens": None,
                                "textRange": {"start": 166, "end": 178},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581data\u2581in",
                                    "logprob": -7.114713668823242,
                                    "raw_logprob": -7.114713668823242,
                                },
                                "topTokens": None,
                                "textRange": {"start": 178, "end": 186},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581a\u2581way\u2581to\u2581make",
                                    "logprob": -2.1352782249450684,
                                    "raw_logprob": -2.1352782249450684,
                                },
                                "topTokens": None,
                                "textRange": {"start": 186, "end": 200},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581the\u2581best\u2581possible",
                                    "logprob": -1.202060341835022,
                                    "raw_logprob": -1.202060341835022,
                                },
                                "topTokens": None,
                                "textRange": {"start": 200, "end": 218},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581choice",
                                    "logprob": -0.49673229455947876,
                                    "raw_logprob": -0.49673229455947876,
                                },
                                "topTokens": None,
                                "textRange": {"start": 218, "end": 225},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.08440639078617096,
                                    "raw_logprob": -0.08440639078617096,
                                },
                                "topTokens": None,
                                "textRange": {"start": 225, "end": 226},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -1.4274420738220215,
                                    "raw_logprob": -1.4274420738220215,
                                },
                                "topTokens": None,
                                "textRange": {"start": 226, "end": 227},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.002755180699750781,
                                    "raw_logprob": -0.002755180699750781,
                                },
                                "topTokens": None,
                                "textRange": {"start": 227, "end": 228},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581However",
                                    "logprob": -2.9974615573883057,
                                    "raw_logprob": -2.9974615573883057,
                                },
                                "topTokens": None,
                                "textRange": {"start": 228, "end": 235},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.0017327546374872327,
                                    "raw_logprob": -0.0017327546374872327,
                                },
                                "topTokens": None,
                                "textRange": {"start": 235, "end": 236},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581sometimes",
                                    "logprob": -2.893026113510132,
                                    "raw_logprob": -2.893026113510132,
                                },
                                "topTokens": None,
                                "textRange": {"start": 236, "end": 246},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581things",
                                    "logprob": -4.238265037536621,
                                    "raw_logprob": -4.238265037536621,
                                },
                                "topTokens": None,
                                "textRange": {"start": 246, "end": 253},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581don't",
                                    "logprob": -2.367069721221924,
                                    "raw_logprob": -2.367069721221924,
                                },
                                "topTokens": None,
                                "textRange": {"start": 253, "end": 259},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581turn\u2581out",
                                    "logprob": -1.7048457860946655,
                                    "raw_logprob": -1.7048457860946655,
                                },
                                "topTokens": None,
                                "textRange": {"start": 259, "end": 268},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581the\u2581way\u2581you",
                                    "logprob": -2.1934995651245117,
                                    "raw_logprob": -2.1934995651245117,
                                },
                                "topTokens": None,
                                "textRange": {"start": 268, "end": 280},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581intended",
                                    "logprob": -3.7538819313049316,
                                    "raw_logprob": -3.7538819313049316,
                                },
                                "topTokens": None,
                                "textRange": {"start": 280, "end": 289},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.41568616032600403,
                                    "raw_logprob": -0.41568616032600403,
                                },
                                "topTokens": None,
                                "textRange": {"start": 289, "end": 290},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581Your",
                                    "logprob": -4.143064498901367,
                                    "raw_logprob": -4.143064498901367,
                                },
                                "topTokens": None,
                                "textRange": {"start": 290, "end": 295},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581decision",
                                    "logprob": -1.1384129524230957,
                                    "raw_logprob": -1.1384129524230957,
                                },
                                "topTokens": None,
                                "textRange": {"start": 295, "end": 304},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581might\u2581not\u2581work",
                                    "logprob": -2.4380242824554443,
                                    "raw_logprob": -2.4380242824554443,
                                },
                                "topTokens": None,
                                "textRange": {"start": 304, "end": 319},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581as\u2581intended",
                                    "logprob": -2.9615366458892822,
                                    "raw_logprob": -2.9615366458892822,
                                },
                                "topTokens": None,
                                "textRange": {"start": 319, "end": 331},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.22413745522499084,
                                    "raw_logprob": -0.22413745522499084,
                                },
                                "topTokens": None,
                                "textRange": {"start": 331, "end": 332},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581or",
                                    "logprob": -0.4422154128551483,
                                    "raw_logprob": -0.4422154128551483,
                                },
                                "topTokens": None,
                                "textRange": {"start": 332, "end": 335},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581act\u2581in",
                                    "logprob": -16.771242141723633,
                                    "raw_logprob": -16.771242141723633,
                                },
                                "topTokens": None,
                                "textRange": {"start": 335, "end": 342},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581unforeseen",
                                    "logprob": -2.0343406200408936,
                                    "raw_logprob": -2.0343406200408936,
                                },
                                "topTokens": None,
                                "textRange": {"start": 342, "end": 353},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581ways",
                                    "logprob": -0.03732850402593613,
                                    "raw_logprob": -0.03732850402593613,
                                },
                                "topTokens": None,
                                "textRange": {"start": 353, "end": 358},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.07006527483463287,
                                    "raw_logprob": -0.07006527483463287,
                                },
                                "topTokens": None,
                                "textRange": {"start": 358, "end": 359},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581Or",
                                    "logprob": -4.574007511138916,
                                    "raw_logprob": -4.574007511138916,
                                },
                                "topTokens": None,
                                "textRange": {"start": 359, "end": 362},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.35941576957702637,
                                    "raw_logprob": -0.35941576957702637,
                                },
                                "topTokens": None,
                                "textRange": {"start": 362, "end": 363},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581you\u2581might\u2581find",
                                    "logprob": -3.0860962867736816,
                                    "raw_logprob": -3.0860962867736816,
                                },
                                "topTokens": None,
                                "textRange": {"start": 363, "end": 378},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581new\u2581information",
                                    "logprob": -3.0317506790161133,
                                    "raw_logprob": -3.0317506790161133,
                                },
                                "topTokens": None,
                                "textRange": {"start": 378, "end": 394},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581or",
                                    "logprob": -3.251086950302124,
                                    "raw_logprob": -3.251086950302124,
                                },
                                "topTokens": None,
                                "textRange": {"start": 394, "end": 397},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581context",
                                    "logprob": -4.189438343048096,
                                    "raw_logprob": -4.189438343048096,
                                },
                                "topTokens": None,
                                "textRange": {"start": 397, "end": 405},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581that\u2581causes",
                                    "logprob": -4.464134216308594,
                                    "raw_logprob": -4.464134216308594,
                                },
                                "topTokens": None,
                                "textRange": {"start": 405, "end": 417},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581you",
                                    "logprob": -0.2493533492088318,
                                    "raw_logprob": -0.2493533492088318,
                                },
                                "topTokens": None,
                                "textRange": {"start": 417, "end": 421},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581to\u2581question",
                                    "logprob": -2.251695156097412,
                                    "raw_logprob": -2.251695156097412,
                                },
                                "topTokens": None,
                                "textRange": {"start": 421, "end": 433},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581your\u2581decision",
                                    "logprob": -1.989322543144226,
                                    "raw_logprob": -1.989322543144226,
                                },
                                "topTokens": None,
                                "textRange": {"start": 433, "end": 447},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.17142613232135773,
                                    "raw_logprob": -0.17142613232135773,
                                },
                                "topTokens": None,
                                "textRange": {"start": 447, "end": 448},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581That's",
                                    "logprob": -5.326101303100586,
                                    "raw_logprob": -5.326101303100586,
                                },
                                "topTokens": None,
                                "textRange": {"start": 448, "end": 455},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581okay",
                                    "logprob": -0.7236325740814209,
                                    "raw_logprob": -0.7236325740814209,
                                },
                                "topTokens": None,
                                "textRange": {"start": 455, "end": 460},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -1.1485638618469238,
                                    "raw_logprob": -1.1485638618469238,
                                },
                                "topTokens": None,
                                "textRange": {"start": 460, "end": 461},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -1.3378857374191284,
                                    "raw_logprob": -1.3378857374191284,
                                },
                                "topTokens": None,
                                "textRange": {"start": 461, "end": 462},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.00016985881666187197,
                                    "raw_logprob": -0.00016985881666187197,
                                },
                                "topTokens": None,
                                "textRange": {"start": 462, "end": 463},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581It's\u2581important\u2581to",
                                    "logprob": -3.5227854251861572,
                                    "raw_logprob": -3.5227854251861572,
                                },
                                "topTokens": None,
                                "textRange": {"start": 463, "end": 480},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581have",
                                    "logprob": -2.9167816638946533,
                                    "raw_logprob": -2.9167816638946533,
                                },
                                "topTokens": None,
                                "textRange": {"start": 480, "end": 485},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581courage",
                                    "logprob": -5.581697940826416,
                                    "raw_logprob": -5.581697940826416,
                                },
                                "topTokens": None,
                                "textRange": {"start": 485, "end": 493},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581when\u2581you're",
                                    "logprob": -4.5586161613464355,
                                    "raw_logprob": -4.5586161613464355,
                                },
                                "topTokens": None,
                                "textRange": {"start": 493, "end": 505},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581a\u2581leader",
                                    "logprob": -0.26272106170654297,
                                    "raw_logprob": -0.26272106170654297,
                                },
                                "topTokens": None,
                                "textRange": {"start": 505, "end": 514},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.3965468406677246,
                                    "raw_logprob": -0.3965468406677246,
                                },
                                "topTokens": None,
                                "textRange": {"start": 514, "end": 515},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581This\u2581means",
                                    "logprob": -2.841196298599243,
                                    "raw_logprob": -2.841196298599243,
                                },
                                "topTokens": None,
                                "textRange": {"start": 515, "end": 526},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581being",
                                    "logprob": -0.4315812587738037,
                                    "raw_logprob": -0.4315812587738037,
                                },
                                "topTokens": None,
                                "textRange": {"start": 526, "end": 532},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581willing\u2581to",
                                    "logprob": -0.03861286863684654,
                                    "raw_logprob": -0.03861286863684654,
                                },
                                "topTokens": None,
                                "textRange": {"start": 532, "end": 543},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581think",
                                    "logprob": -7.899557113647461,
                                    "raw_logprob": -7.899557113647461,
                                },
                                "topTokens": None,
                                "textRange": {"start": 543, "end": 549},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581critically",
                                    "logprob": -0.6595878601074219,
                                    "raw_logprob": -0.6595878601074219,
                                },
                                "topTokens": None,
                                "textRange": {"start": 549, "end": 560},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -1.2396876811981201,
                                    "raw_logprob": -1.2396876811981201,
                                },
                                "topTokens": None,
                                "textRange": {"start": 560, "end": 561},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581reflect",
                                    "logprob": -6.496954917907715,
                                    "raw_logprob": -6.496954917907715,
                                },
                                "topTokens": None,
                                "textRange": {"start": 561, "end": 569},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.3813382685184479,
                                    "raw_logprob": -0.3813382685184479,
                                },
                                "topTokens": None,
                                "textRange": {"start": 569, "end": 570},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581learn\u2581from",
                                    "logprob": -5.863975524902344,
                                    "raw_logprob": -5.863975524902344,
                                },
                                "topTokens": None,
                                "textRange": {"start": 570, "end": 581},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581mistakes",
                                    "logprob": -1.1053953170776367,
                                    "raw_logprob": -1.1053953170776367,
                                },
                                "topTokens": None,
                                "textRange": {"start": 581, "end": 590},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.010977472178637981,
                                    "raw_logprob": -0.010977472178637981,
                                },
                                "topTokens": None,
                                "textRange": {"start": 590, "end": 591},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and",
                                    "logprob": -0.5951434373855591,
                                    "raw_logprob": -0.5951434373855591,
                                },
                                "topTokens": None,
                                "textRange": {"start": 591, "end": 595},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581take\u2581action",
                                    "logprob": -4.118521690368652,
                                    "raw_logprob": -4.118521690368652,
                                },
                                "topTokens": None,
                                "textRange": {"start": 595, "end": 607},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581steps",
                                    "logprob": -8.071130752563477,
                                    "raw_logprob": -8.071130752563477,
                                },
                                "topTokens": None,
                                "textRange": {"start": 607, "end": 613},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581moving\u2581forward",
                                    "logprob": -5.662147045135498,
                                    "raw_logprob": -5.662147045135498,
                                },
                                "topTokens": None,
                                "textRange": {"start": 613, "end": 628},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.03737432509660721,
                                    "raw_logprob": -0.03737432509660721,
                                },
                                "topTokens": None,
                                "textRange": {"start": 628, "end": 629},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -1.0259989500045776,
                                    "raw_logprob": -1.0259989500045776,
                                },
                                "topTokens": None,
                                "textRange": {"start": 629, "end": 630},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.0006999903125688434,
                                    "raw_logprob": -0.0006999903125688434,
                                },
                                "topTokens": None,
                                "textRange": {"start": 630, "end": 631},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581There\u2581are\u2581three",
                                    "logprob": -5.931296348571777,
                                    "raw_logprob": -5.931296348571777,
                                },
                                "topTokens": None,
                                "textRange": {"start": 631, "end": 646},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581steps",
                                    "logprob": -2.7536213397979736,
                                    "raw_logprob": -2.7536213397979736,
                                },
                                "topTokens": None,
                                "textRange": {"start": 646, "end": 652},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581that\u2581can\u2581help\u2581you",
                                    "logprob": -2.3474459648132324,
                                    "raw_logprob": -2.3474459648132324,
                                },
                                "topTokens": None,
                                "textRange": {"start": 652, "end": 670},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581grow",
                                    "logprob": -7.027171611785889,
                                    "raw_logprob": -7.027171611785889,
                                },
                                "topTokens": None,
                                "textRange": {"start": 670, "end": 675},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581as\u2581a\u2581leader",
                                    "logprob": -0.40542012453079224,
                                    "raw_logprob": -0.40542012453079224,
                                },
                                "topTokens": None,
                                "textRange": {"start": 675, "end": 687},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and\u2581make",
                                    "logprob": -0.7026352882385254,
                                    "raw_logprob": -0.7026352882385254,
                                },
                                "topTokens": None,
                                "textRange": {"start": 687, "end": 696},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581better",
                                    "logprob": -2.1509532928466797,
                                    "raw_logprob": -2.1509532928466797,
                                },
                                "topTokens": None,
                                "textRange": {"start": 696, "end": 703},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581business\u2581decisions",
                                    "logprob": -0.24822193384170532,
                                    "raw_logprob": -0.24822193384170532,
                                },
                                "topTokens": None,
                                "textRange": {"start": 703, "end": 722},
                            },
                            {
                                "generatedToken": {
                                    "token": ":",
                                    "logprob": -0.46704334020614624,
                                    "raw_logprob": -0.46704334020614624,
                                },
                                "topTokens": None,
                                "textRange": {"start": 722, "end": 723},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.02775048278272152,
                                    "raw_logprob": -0.02775048278272152,
                                },
                                "topTokens": None,
                                "textRange": {"start": 723, "end": 724},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.0020361661445349455,
                                    "raw_logprob": -0.0020361661445349455,
                                },
                                "topTokens": None,
                                "textRange": {"start": 724, "end": 725},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581Step",
                                    "logprob": -1.442288875579834,
                                    "raw_logprob": -1.442288875579834,
                                },
                                "topTokens": None,
                                "textRange": {"start": 725, "end": 729},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581",
                                    "logprob": -0.05165497958660126,
                                    "raw_logprob": -0.05165497958660126,
                                },
                                "topTokens": None,
                                "textRange": {"start": 729, "end": 730},
                            },
                            {
                                "generatedToken": {
                                    "token": "1",
                                    "logprob": -4.792098479811102e-05,
                                    "raw_logprob": -4.792098479811102e-05,
                                },
                                "topTokens": None,
                                "textRange": {"start": 730, "end": 731},
                            },
                            {
                                "generatedToken": {
                                    "token": ":",
                                    "logprob": -0.02608294039964676,
                                    "raw_logprob": -0.02608294039964676,
                                },
                                "topTokens": None,
                                "textRange": {"start": 731, "end": 732},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581Gather",
                                    "logprob": -3.0909531116485596,
                                    "raw_logprob": -3.0909531116485596,
                                },
                                "topTokens": None,
                                "textRange": {"start": 732, "end": 739},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581information",
                                    "logprob": -0.8507784605026245,
                                    "raw_logprob": -0.8507784605026245,
                                },
                                "topTokens": None,
                                "textRange": {"start": 739, "end": 751},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.6048281788825989,
                                    "raw_logprob": -0.6048281788825989,
                                },
                                "topTokens": None,
                                "textRange": {"start": 751, "end": 752},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.01351175270974636,
                                    "raw_logprob": -0.01351175270974636,
                                },
                                "topTokens": None,
                                "textRange": {"start": 752, "end": 753},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581The\u2581first\u2581step",
                                    "logprob": -2.7363672256469727,
                                    "raw_logprob": -2.7363672256469727,
                                },
                                "topTokens": None,
                                "textRange": {"start": 753, "end": 767},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581to",
                                    "logprob": -0.1339748501777649,
                                    "raw_logprob": -0.1339748501777649,
                                },
                                "topTokens": None,
                                "textRange": {"start": 767, "end": 770},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581making",
                                    "logprob": -0.3207220137119293,
                                    "raw_logprob": -0.3207220137119293,
                                },
                                "topTokens": None,
                                "textRange": {"start": 770, "end": 777},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581a\u2581good",
                                    "logprob": -0.6057114005088806,
                                    "raw_logprob": -0.6057114005088806,
                                },
                                "topTokens": None,
                                "textRange": {"start": 777, "end": 784},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581decision",
                                    "logprob": -0.030523210763931274,
                                    "raw_logprob": -0.030523210763931274,
                                },
                                "topTokens": None,
                                "textRange": {"start": 784, "end": 793},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581is\u2581to",
                                    "logprob": -3.0425467491149902,
                                    "raw_logprob": -3.0425467491149902,
                                },
                                "topTokens": None,
                                "textRange": {"start": 793, "end": 799},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581make\u2581sure\u2581that\u2581you\u2581have",
                                    "logprob": -0.7047816514968872,
                                    "raw_logprob": -0.7047816514968872,
                                },
                                "topTokens": None,
                                "textRange": {"start": 799, "end": 823},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581all\u2581of\u2581the",
                                    "logprob": -1.9955559968948364,
                                    "raw_logprob": -1.9955559968948364,
                                },
                                "topTokens": None,
                                "textRange": {"start": 823, "end": 834},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581facts",
                                    "logprob": -2.409013271331787,
                                    "raw_logprob": -2.409013271331787,
                                },
                                "topTokens": None,
                                "textRange": {"start": 834, "end": 840},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.2631763517856598,
                                    "raw_logprob": -0.2631763517856598,
                                },
                                "topTokens": None,
                                "textRange": {"start": 840, "end": 841},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581It's\u2581important\u2581to",
                                    "logprob": -4.5646491050720215,
                                    "raw_logprob": -4.5646491050720215,
                                },
                                "topTokens": None,
                                "textRange": {"start": 841, "end": 859},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581know\u2581what",
                                    "logprob": -6.077958106994629,
                                    "raw_logprob": -6.077958106994629,
                                },
                                "topTokens": None,
                                "textRange": {"start": 859, "end": 869},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581information",
                                    "logprob": -2.0120184421539307,
                                    "raw_logprob": -2.0120184421539307,
                                },
                                "topTokens": None,
                                "textRange": {"start": 869, "end": 881},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581you\u2581need",
                                    "logprob": -1.7770088911056519,
                                    "raw_logprob": -1.7770088911056519,
                                },
                                "topTokens": None,
                                "textRange": {"start": 881, "end": 890},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.4962013363838196,
                                    "raw_logprob": -0.4962013363838196,
                                },
                                "topTokens": None,
                                "textRange": {"start": 890, "end": 891},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and",
                                    "logprob": -0.8423260450363159,
                                    "raw_logprob": -0.8423260450363159,
                                },
                                "topTokens": None,
                                "textRange": {"start": 891, "end": 895},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581from\u2581where",
                                    "logprob": -8.261597633361816,
                                    "raw_logprob": -8.261597633361816,
                                },
                                "topTokens": None,
                                "textRange": {"start": 895, "end": 906},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581to\u2581get\u2581it",
                                    "logprob": -0.985969066619873,
                                    "raw_logprob": -0.985969066619873,
                                },
                                "topTokens": None,
                                "textRange": {"start": 906, "end": 916},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.0048598977737128735,
                                    "raw_logprob": -0.0048598977737128735,
                                },
                                "topTokens": None,
                                "textRange": {"start": 916, "end": 917},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.5743589401245117,
                                    "raw_logprob": -0.5743589401245117,
                                },
                                "topTokens": None,
                                "textRange": {"start": 917, "end": 918},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.000593962671700865,
                                    "raw_logprob": -0.000593962671700865,
                                },
                                "topTokens": None,
                                "textRange": {"start": 918, "end": 919},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581You\u2581can",
                                    "logprob": -4.267513275146484,
                                    "raw_logprob": -4.267513275146484,
                                },
                                "topTokens": None,
                                "textRange": {"start": 919, "end": 926},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581gather",
                                    "logprob": -0.007923126220703125,
                                    "raw_logprob": -0.007923126220703125,
                                },
                                "topTokens": None,
                                "textRange": {"start": 926, "end": 933},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581information",
                                    "logprob": -0.3179577887058258,
                                    "raw_logprob": -0.3179577887058258,
                                },
                                "topTokens": None,
                                "textRange": {"start": 933, "end": 945},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581by\u2581doing",
                                    "logprob": -5.132864952087402,
                                    "raw_logprob": -5.132864952087402,
                                },
                                "topTokens": None,
                                "textRange": {"start": 945, "end": 954},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581things\u2581like",
                                    "logprob": -2.202630043029785,
                                    "raw_logprob": -2.202630043029785,
                                },
                                "topTokens": None,
                                "textRange": {"start": 954, "end": 966},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581reading",
                                    "logprob": -3.232940196990967,
                                    "raw_logprob": -3.232940196990967,
                                },
                                "topTokens": None,
                                "textRange": {"start": 966, "end": 974},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581reports",
                                    "logprob": -0.329463928937912,
                                    "raw_logprob": -0.329463928937912,
                                },
                                "topTokens": None,
                                "textRange": {"start": 974, "end": 982},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.002441998338326812,
                                    "raw_logprob": -0.002441998338326812,
                                },
                                "topTokens": None,
                                "textRange": {"start": 982, "end": 983},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581talking\u2581to",
                                    "logprob": -0.12298407405614853,
                                    "raw_logprob": -0.12298407405614853,
                                },
                                "topTokens": None,
                                "textRange": {"start": 983, "end": 994},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581stakeholders",
                                    "logprob": -2.3864426612854004,
                                    "raw_logprob": -2.3864426612854004,
                                },
                                "topTokens": None,
                                "textRange": {"start": 994, "end": 1007},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.012393603101372719,
                                    "raw_logprob": -0.012393603101372719,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1007, "end": 1008},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and",
                                    "logprob": -0.1544899344444275,
                                    "raw_logprob": -0.1544899344444275,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1008, "end": 1012},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581conducting\u2581research",
                                    "logprob": -0.731350839138031,
                                    "raw_logprob": -0.731350839138031,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1012, "end": 1032},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.010276736691594124,
                                    "raw_logprob": -0.010276736691594124,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1032, "end": 1033},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -1.247491478919983,
                                    "raw_logprob": -1.247491478919983,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1033, "end": 1034},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -5.7338023907504976e-05,
                                    "raw_logprob": -5.7338023907504976e-05,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1034, "end": 1035},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581Step",
                                    "logprob": -0.43501779437065125,
                                    "raw_logprob": -0.43501779437065125,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1035, "end": 1039},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581",
                                    "logprob": -1.1920858014491387e-05,
                                    "raw_logprob": -1.1920858014491387e-05,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1039, "end": 1040},
                            },
                            {
                                "generatedToken": {
                                    "token": "2",
                                    "logprob": -0.00016342257731594145,
                                    "raw_logprob": -0.00016342257731594145,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1040, "end": 1041},
                            },
                            {
                                "generatedToken": {
                                    "token": ":",
                                    "logprob": -0.00010644822759786621,
                                    "raw_logprob": -0.00010644822759786621,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1041, "end": 1042},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581Analyze",
                                    "logprob": -0.15760670602321625,
                                    "raw_logprob": -0.15760670602321625,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1042, "end": 1050},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581information",
                                    "logprob": -1.612084984779358,
                                    "raw_logprob": -1.612084984779358,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1050, "end": 1062},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -9.583967766957358e-05,
                                    "raw_logprob": -9.583967766957358e-05,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1062, "end": 1063},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.00024685196694917977,
                                    "raw_logprob": -0.00024685196694917977,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1063, "end": 1064},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581Once\u2581you've",
                                    "logprob": -2.3116512298583984,
                                    "raw_logprob": -2.3116512298583984,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1064, "end": 1075},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581gathered",
                                    "logprob": -0.002062814310193062,
                                    "raw_logprob": -0.002062814310193062,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1075, "end": 1084},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581all\u2581of\u2581your",
                                    "logprob": -2.685849666595459,
                                    "raw_logprob": -2.685849666595459,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1084, "end": 1096},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581information",
                                    "logprob": -0.003219066886231303,
                                    "raw_logprob": -0.003219066886231303,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1096, "end": 1108},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -3.361645576660521e-05,
                                    "raw_logprob": -3.361645576660521e-05,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1108, "end": 1109},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581you\u2581need\u2581to",
                                    "logprob": -1.4020256996154785,
                                    "raw_logprob": -1.4020256996154785,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1109, "end": 1121},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581take\u2581some\u2581time\u2581to",
                                    "logprob": -2.1766977310180664,
                                    "raw_logprob": -2.1766977310180664,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1121, "end": 1139},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581think\u2581about\u2581it",
                                    "logprob": -0.4216986298561096,
                                    "raw_logprob": -0.4216986298561096,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1139, "end": 1154},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.24139046669006348,
                                    "raw_logprob": -0.24139046669006348,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1154, "end": 1155},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581You\u2581need\u2581to",
                                    "logprob": -1.129857063293457,
                                    "raw_logprob": -1.129857063293457,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1155, "end": 1167},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581analyze\u2581the",
                                    "logprob": -1.3527189493179321,
                                    "raw_logprob": -1.3527189493179321,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1167, "end": 1179},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581data",
                                    "logprob": -1.0173096656799316,
                                    "raw_logprob": -1.0173096656799316,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1179, "end": 1184},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and\u2581identify",
                                    "logprob": -3.182776927947998,
                                    "raw_logprob": -3.182776927947998,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1184, "end": 1197},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581patterns",
                                    "logprob": -0.6117339134216309,
                                    "raw_logprob": -0.6117339134216309,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1197, "end": 1206},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -0.4564504325389862,
                                    "raw_logprob": -0.4564504325389862,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1206, "end": 1207},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581trends",
                                    "logprob": -0.0026252351235598326,
                                    "raw_logprob": -0.0026252351235598326,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1207, "end": 1214},
                            },
                            {
                                "generatedToken": {
                                    "token": ",",
                                    "logprob": -2.706014311115723e-05,
                                    "raw_logprob": -2.706014311115723e-05,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1214, "end": 1215},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581and",
                                    "logprob": -0.16668428480625153,
                                    "raw_logprob": -0.16668428480625153,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1215, "end": 1219},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581trends",
                                    "logprob": -2.091916084289551,
                                    "raw_logprob": -2.091916084289551,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1219, "end": 1226},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581that",
                                    "logprob": -2.99127197265625,
                                    "raw_logprob": -2.99127197265625,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1226, "end": 1231},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581might\u2581not\u2581be",
                                    "logprob": -2.1681160926818848,
                                    "raw_logprob": -2.1681160926818848,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1231, "end": 1244},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581immediately",
                                    "logprob": -0.5720977783203125,
                                    "raw_logprob": -0.5720977783203125,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1244, "end": 1256},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581obvious",
                                    "logprob": -0.38135844469070435,
                                    "raw_logprob": -0.38135844469070435,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1256, "end": 1264},
                            },
                            {
                                "generatedToken": {
                                    "token": ".",
                                    "logprob": -0.0025424794293940067,
                                    "raw_logprob": -0.0025424794293940067,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1264, "end": 1265},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.005445053335279226,
                                    "raw_logprob": -0.005445053335279226,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1265, "end": 1266},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -1.156323378381785e-05,
                                    "raw_logprob": -1.156323378381785e-05,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1266, "end": 1267},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581There\u2581are\u2581a\u2581few",
                                    "logprob": -4.2585649490356445,
                                    "raw_logprob": -4.2585649490356445,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1267, "end": 1282},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581things",
                                    "logprob": -2.04957914352417,
                                    "raw_logprob": -2.04957914352417,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1282, "end": 1289},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581you\u2581should",
                                    "logprob": -1.8114514350891113,
                                    "raw_logprob": -1.8114514350891113,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1289, "end": 1300},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581keep\u2581in\u2581mind",
                                    "logprob": -0.2850663959980011,
                                    "raw_logprob": -0.2850663959980011,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1300, "end": 1313},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581when\u2581you're",
                                    "logprob": -0.40983426570892334,
                                    "raw_logprob": -0.40983426570892334,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1313, "end": 1325},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581analyzing",
                                    "logprob": -0.049553561955690384,
                                    "raw_logprob": -0.049553561955690384,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1325, "end": 1335},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581information",
                                    "logprob": -0.0341101810336113,
                                    "raw_logprob": -0.0341101810336113,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1335, "end": 1347},
                            },
                            {
                                "generatedToken": {
                                    "token": ":",
                                    "logprob": -0.4348779022693634,
                                    "raw_logprob": -0.4348779022693634,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1347, "end": 1348},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.006193492095917463,
                                    "raw_logprob": -0.006193492095917463,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1348, "end": 1349},
                            },
                            {
                                "generatedToken": {
                                    "token": "<|newline|>",
                                    "logprob": -0.000358159770257771,
                                    "raw_logprob": -0.000358159770257771,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1349, "end": 1350},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581*",
                                    "logprob": -1.0053796768188477,
                                    "raw_logprob": -1.0053796768188477,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1350, "end": 1351},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581Identify",
                                    "logprob": -4.100193977355957,
                                    "raw_logprob": -4.100193977355957,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1351, "end": 1360},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581the",
                                    "logprob": -1.141700029373169,
                                    "raw_logprob": -1.141700029373169,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1360, "end": 1364},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581key\u2581points",
                                    "logprob": -0.9346644282341003,
                                    "raw_logprob": -0.9346644282341003,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1364, "end": 1375},
                            },
                            {
                                "generatedToken": {
                                    "token": ":",
                                    "logprob": -0.29478567838668823,
                                    "raw_logprob": -0.29478567838668823,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1375, "end": 1376},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581What\u2581are\u2581the",
                                    "logprob": -0.2456199824810028,
                                    "raw_logprob": -0.2456199824810028,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1376, "end": 1389},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581key",
                                    "logprob": -0.8171483278274536,
                                    "raw_logprob": -0.8171483278274536,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1389, "end": 1393},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581takeaways",
                                    "logprob": -0.5598645806312561,
                                    "raw_logprob": -0.5598645806312561,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1393, "end": 1403},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581from",
                                    "logprob": -1.6096564531326294,
                                    "raw_logprob": -1.6096564531326294,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1403, "end": 1408},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581this\u2581information",
                                    "logprob": -1.101968765258789,
                                    "raw_logprob": -1.101968765258789,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1408, "end": 1425},
                            },
                            {
                                "generatedToken": {
                                    "token": "?",
                                    "logprob": -0.0003685271949507296,
                                    "raw_logprob": -0.0003685271949507296,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1425, "end": 1426},
                            },
                            {
                                "generatedToken": {
                                    "token": "\u2581What",
                                    "logprob": -2.42529034614563,
                                    "raw_logprob": -2.42529034614563,
                                },
                                "topTokens": None,
                                "textRange": {"start": 1426, "end": 1431},
                            },
                        ],
                    },
                    "finishReason": {"reason": "length", "length": 200},
                }
            ],
        },
    ],
    "cohere.command-text-v14::Write me a blog about making strong business decisions as a leader.": [
        {},
        {
            "generations": [
                {
                    "id": "7449e005-a317-42ab-8e47-6bf0fa119088",
                    "text": " As a leader, one of the most important things you can do is make strong business decisions. Your choices can make or break your company, so it's essential to take the time to think things through and consider all your options. Here are a few tips for making sound business decisions:\n\n1. Do your research. Before making any decision, it's important to gather as much information as possible. This means talking to your team, looking at data and trends, and considering all of your options. The more information you have, the better equipped you'll be to make a decision.\n\n2. Consider the consequences. Every decision has consequences, so it's important to think about what might happen as a result of your choice. What will the impact be on your team, your company, and your customers? It's also important to think about how your decision might affect your own career and personal life.\n\n3. Seek advice. If you're struggling to make a decision, it",
                }
            ],
            "id": "4e3ebf15-98d2-4aaf-a2da-61d0e262e862",
            "prompt": "Write me a blog about making strong business decisions as a leader.",
        },
    ],
}

MODEL_PATH_RE = re.compile(r"/model/([^/]+)/invoke")


def simple_get(self):
    content_len = int(self.headers.get("content-length"))
    content = json.loads(self.rfile.read(content_len).decode("utf-8"))

    model = MODEL_PATH_RE.match(self.path).group(1)
    prompt = extract_shortened_prompt(content, model)
    if not prompt:
        self.send_response(500)
        self.end_headers()
        self.wfile.write("Could not parse prompt.".encode("utf-8"))
        return

    headers, response = ({}, "")
    for k, v in RESPONSES.items():
        if prompt.startswith(k):
            headers, response = v
            break
    else:  # If no matches found
        self.send_response(500)
        self.end_headers()
        self.wfile.write(("Unknown Prompt:\n%s" % prompt).encode("utf-8"))
        return

    # Send response code
    self.send_response(200)

    # Send headers
    for k, v in headers.items():
        self.send_header(k, v)
    self.end_headers()

    # Send response body
    self.wfile.write(json.dumps(response).encode("utf-8"))
    return


def extract_shortened_prompt(content, model):
    prompt = content.get("inputText", None) or content.get("prompt", None)
    prompt = "::".join((model, prompt))  # Prepend model name to prompt key to keep separate copies
    return prompt.lstrip().split("\n")[0]


class MockExternalBedrockServer(MockExternalHTTPServer):
    # To use this class in a test one needs to start and stop this server
    # before and after making requests to the test app that makes the external
    # calls.

    def __init__(self, handler=simple_get, port=None, *args, **kwargs):
        super(MockExternalBedrockServer, self).__init__(handler=handler, port=port, *args, **kwargs)


if __name__ == "__main__":
    with MockExternalBedrockServer() as server:
        print("MockExternalBedrockServer serving on port %s" % str(server.port))
        while True:
            pass  # Serve forever
