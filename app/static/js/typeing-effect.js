// 打字效果类
class TypingEffect {
    constructor(elementId, textList, options = {}) {
        this.typingElement = document.getElementById(elementId);
        this.textList = textList;
        this.currentIndex = 0;

        // 默认配置
        this.options = {
            typingSpeed: 100,    // 打字速度(ms)
            backspaceSpeed: 50,  // 回退速度(ms)
            displayDuration: 1000, // 显示持续时间(ms)
            pauseAfterDelete: 300 // 删除后暂停时间(ms)
        };

        // 合并用户自定义配置
        Object.assign(this.options, options);
    }

    // 打字效果
    typeWriter(text, i, callback) {
        if (i < text.length) {
            this.typingElement.textContent = text.substring(0, i + 1);
            setTimeout(() => this.typeWriter(text, i + 1, callback), this.options.typingSpeed);
        } else if (typeof callback === 'function') {
            setTimeout(callback, this.options.displayDuration);
        }
    }

    // 回退效果
    backspace(text, i, callback) {
        if (i >= 0) {
            this.typingElement.textContent = text.substring(0, i) || '';
            setTimeout(() => this.backspace(text, i - 1, callback), this.options.backspaceSpeed);
        } else if (typeof callback === 'function') {
            setTimeout(callback, this.options.pauseAfterDelete);
        }
    }

    // 开始动画
    start() {
        if (this.currentIndex < this.textList.length) {
            const text = this.textList[this.currentIndex];
            this.typingElement.textContent = '';

            this.typeWriter(text, 0, () => {
                setTimeout(() => {
                    this.backspace(text, text.length, () => {
                        this.currentIndex = (this.currentIndex + 1) % this.textList.length;
                        this.start();
                    });
                }, this.options.displayDuration);
            });
        }
    }
}


const textList = [
    "德为心守，意为身牧",
    "缺月挂疏桐，漏断人初静"
];

// 创建实例并启动
const typingEffect = new TypingEffect('description', textList, {
    typingSpeed: 100,
    backspaceSpeed: 50,
    displayDuration: 1000,
    pauseAfterDelete: 300
});

typingEffect.start();