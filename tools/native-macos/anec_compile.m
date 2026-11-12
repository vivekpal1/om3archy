// anec_compile MIL OUT_DIR NAME TARGET: compile one MIL file with this Mac's ANECompiler.
#import <Foundation/Foundation.h>
#import <dlfcn.h>

typedef void (^ANECCompileBlock)(int status, CFDictionaryRef result);
typedef void (*ANECCompileFn)(CFDictionaryRef, CFDictionaryRef, ANECCompileBlock);
typedef CFDictionaryRef (*ANECCreateInputFn)(const char *);

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 5) { fprintf(stderr, "usage: %s MIL OUT_DIR NAME TARGET\n", argv[0]); return 64; }
        void *lib = dlopen("/System/Library/PrivateFrameworks/ANECompiler.framework/ANECompiler", RTLD_NOW | RTLD_LOCAL);
        ANECCompileFn compile = (ANECCompileFn)dlsym(lib, "ANECCompile");
        ANECCreateInputFn createInput = (ANECCreateInputFn)dlsym(lib, "ANECCreateCompilerInputDictionary");
        if (!compile || !createInput) return 4;
        CFDictionaryRef raw = createInput(argv[1]);
        if (!raw) return 5;
        CFMutableDictionaryRef input = CFDictionaryCreateMutableCopy(kCFAllocatorDefault, 0, raw);
        CFDictionarySetValue(input, CFSTR("OutputFileName"), (__bridge CFStringRef)@(argv[3]));
        CFDictionarySetValue(input, CFSTR("OutputFilePath"), (__bridge CFStringRef)[@(argv[2]) stringByAppendingString:@"/"]);
        const void *keys[] = {CFSTR("TargetArchitecture")};
        const void *values[] = {(__bridge CFStringRef)@(argv[4])};
        CFDictionaryRef options = CFDictionaryCreate(kCFAllocatorDefault, keys, values, 1,
            &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
        __block int status = INT_MIN;
        dispatch_semaphore_t done = dispatch_semaphore_create(0);
        compile(input, options, ^(int result, CFDictionaryRef details) { (void)details; status = result; dispatch_semaphore_signal(done); });
        long wait = dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 60 * NSEC_PER_SEC));
        printf("target=%s status=%d wait=%ld\n", argv[4], status, wait);
        return status == 0 && wait == 0 ? 0 : 6;
    }
}
